"""
Comparison Engine Module
Core logic for comparing CCP and AT whitelists
Refactored from compare_whitelists.py for use in GUI
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging
import difflib
import re

logger = logging.getLogger(__name__)

# ================================
# CUSTOM EXCEPTIONS
# ================================

class ValidationError(Exception):
    """Raised when validation fails"""
    pass

class ComparisonError(Exception):
    """Raised when comparison fails"""
    pass

# ================================
# COMPARISON ENGINE CLASS
# ================================

class ComparisonEngine:
    """Main comparison engine for CCP and AT whitelists"""
    
    def __init__(self, file_paths):
        """
        Initialize comparison engine with file paths
        
        Args:
            file_paths: Dictionary of filename -> filepath
        """
        self.file_paths = file_paths
        self.ccp_sec = None
        self.ccp_rules = None
        self.at = None
        self.mapping = None
        self.ccp_combined = None
        self.ccp_symbol_col = None
        self.at_symbol_col = None
        
    def compare(self):
        """
        Run the complete comparison workflow
        
        Returns:
            Dictionary with comparison results
        """
        try:
            logger.info("Starting comparison workflow...")
            
            # Load files
            self._load_files()
            logger.info("Files loaded successfully")
            
            # Normalize columns
            self._normalize_columns()
            logger.info("Columns normalized")
            
            # Validate required columns
            self._validate_columns()
            logger.info("Columns validated")
            
            # Detect symbol columns
            self._detect_symbol_columns()
            logger.info("Symbol columns detected")
            
            # Merge CCP data
            self._merge_ccp()
            logger.info("CCP data merged")
            
            # Prepare mapping
            self._prepare_mapping()
            logger.info("Mapping prepared")
            
            # Create composite keys
            self._create_composite_keys()
            logger.info("Composite keys created")
            
            # Align CCP to AT structure
            self._align_ccp_structure()
            logger.info("CCP structure aligned")
            
            # Run comparisons
            results = self._run_requirements()
            logger.info("Requirements completed")
            
            # Generate statistics
            statistics = self._generate_statistics(results)
            logger.info("Statistics generated")
            
            results['statistics'] = statistics
            
            logger.info("Comparison workflow completed successfully")
            return results
        
        except Exception as e:
            logger.error(f"Comparison failed: {str(e)}")
            raise ComparisonError(f"Comparison failed: {str(e)}")
    
    # ================================
    # STEP 1: LOAD FILES
    # ================================
    
    def _load_files(self):
        """Load all Excel files"""
        try:
            for filename, filepath in self.file_paths.items():
                if 'CCP_Security' in filename:
                    self.ccp_sec = pd.read_excel(filepath)
                elif 'CCP_Market' in filename:
                    self.ccp_rules = pd.read_excel(filepath)
                elif 'AT_Whitelist' in filename:
                    self.at = pd.read_excel(filepath)
                elif 'Column_Mapping' in filename:
                    self.mapping = pd.read_excel(filepath)
            
            # Validate all files loaded
            if self.ccp_sec is None or self.ccp_rules is None or self.at is None or self.mapping is None:
                raise ValidationError("Not all required files were found or loaded")
        
        except Exception as e:
            logger.error(f"Error loading files: {str(e)}")
            raise ValidationError(f"Error loading files: {str(e)}")
    
    # ================================
    # STEP 2: NORMALIZE COLUMNS
    # ================================
    
    def _normalize_columns(self):
        """Normalize column names across all dataframes"""
        for df in [self.ccp_sec, self.ccp_rules, self.at, self.mapping]:
            if df is not None:
                df.columns = (
                    df.columns.astype(str)
                    .str.strip()
                    .str.replace(r"\s+", "_", regex=True)
                    .str.replace(r"__+", "_", regex=True)
                    .str.lower()
                )
    
    # ================================
    # STEP 3: VALIDATE COLUMNS
    # ================================
    
    def _validate_columns(self):
        """Validate that required columns exist"""
        required = {
            'ccp_sec': ['exchange'],
            'ccp_rules': ['exchange'],
            'at': ['exchange'],
            'mapping': ['ccp_column', 'at_column']
        }
        
        dfs = {
            'ccp_sec': self.ccp_sec,
            'ccp_rules': self.ccp_rules,
            'at': self.at,
            'mapping': self.mapping
        }
        
        for name, required_cols in required.items():
            df = dfs[name]
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                raise ValidationError(
                    f"Missing columns {missing} in {name}. "
                    f"Available: {list(df.columns)}"
                )
    
    # ================================
    # STEP 4: DETECT SYMBOL COLUMNS
    # ================================
    
    def _detect_symbol_columns(self):
        """Detect symbol/security ID columns"""
        common_names = ['symbol', 'security_id', 'isin', 'cusip', 'identifier', 'secid']
        
        for col in common_names:
            if col in self.ccp_sec.columns:
                self.ccp_symbol_col = col
                break
        
        for col in common_names:
            if col in self.at.columns:
                self.at_symbol_col = col
                break
        
        if not self.ccp_symbol_col:
            raise ValidationError(f"Could not detect symbol column in CCP. Available: {list(self.ccp_sec.columns)}")
        
        if not self.at_symbol_col:
            raise ValidationError(f"Could not detect symbol column in AT. Available: {list(self.at.columns)}")
    
    # ================================
    # STEP 5: MERGE CCP DATA
    # ================================
    
    def _merge_ccp(self):
        """Merge CCP Security + CCP Market Rules"""
        self.ccp_combined = pd.merge(
            self.ccp_sec,
            self.ccp_rules,
            on="exchange",
            how="left",
            validate="m:1"
        )
    
    # ================================
    # STEP 6: PREPARE MAPPING
    # ================================
    
    def _prepare_mapping(self):
        """Clean and prepare mapping file"""
        self.mapping = self.mapping.dropna(how="all")
        self.mapping = self.mapping.fillna("")
        # Normalize mapping entries using same rules as dataframe column normalization
        def normalize_name(s: str) -> str:
            if s is None:
                return ""
            s = str(s)
            # remove parenthetical notes
            s = re.sub(r"\(.*?\)", "", s)
            # replace common separators with space
            s = s.replace('\r', ' ').replace('\n', ' ').replace('/', ' ').replace('-', ' ')
            # remove non-alphanumeric except spaces
            s = re.sub(r"[^0-9a-zA-Z ]+", "", s)
            # collapse spaces and lowercase
            s = re.sub(r"\s+", " ", s).strip().lower()
            return s

        import re
        self.mapping["ccp_column_raw"] = self.mapping["ccp_column"].astype(str)
        self.mapping["at_column_raw"] = self.mapping["at_column"].astype(str)

        self.mapping["ccp_column_norm"] = self.mapping["ccp_column_raw"].apply(lambda v: normalize_name(v))
        self.mapping["at_column_norm"] = self.mapping["at_column_raw"].apply(lambda v: normalize_name(v))
    
    # ================================
    # STEP 7: CREATE COMPOSITE KEYS
    # ================================
    
    def _create_composite_keys(self):
        """Create composite keys for comparison"""
        # Normalize symbol and exchange: strip whitespace and uppercase for robust matching
        try:
            self.ccp_combined[self.ccp_symbol_col] = (
                self.ccp_combined[self.ccp_symbol_col].astype(str).str.strip().str.upper()
            )
        except Exception:
            self.ccp_combined[self.ccp_symbol_col] = self.ccp_combined[self.ccp_symbol_col].astype(str).str.strip()


        try:
            self.ccp_combined["exchange"] = (
                self.ccp_combined["exchange"].astype(str).str.strip().str.upper()
            )
        except Exception:
            self.ccp_combined["exchange"] = self.ccp_combined["exchange"].astype(str).str.strip()

        try:
            self.at[self.at_symbol_col] = (
                self.at[self.at_symbol_col].astype(str).str.strip().str.upper()
            )
        except Exception:
            self.at[self.at_symbol_col] = self.at[self.at_symbol_col].astype(str).str.strip()

        try:
            self.at["exchange"] = (
                self.at["exchange"].astype(str).str.strip().str.upper()
            )
        except Exception:
            self.at["exchange"] = self.at["exchange"].astype(str).str.strip()

        # Build composite key using normalized values
        self.ccp_combined["composite_key"] = (
            self.ccp_combined[self.ccp_symbol_col].astype(str) + "|" +
            self.ccp_combined["exchange"].astype(str)
        )

        self.at["composite_key"] = (
            self.at[self.at_symbol_col].astype(str) + "|" +
            self.at["exchange"].astype(str)
        )
    
    # ================================
    # STEP 8: ALIGN CCP STRUCTURE
    # ================================
    
    def _align_ccp_structure(self):
        """Align CCP columns to AT structure"""
        aligned_ccp = pd.DataFrame()
        aligned_ccp[self.at_symbol_col] = self.ccp_combined[self.ccp_symbol_col]
        aligned_ccp["exchange"] = self.ccp_combined["exchange"]
        aligned_ccp["composite_key"] = self.ccp_combined["composite_key"]
        
        # Map columns according to mapping file
        # Build normalized lookup maps for available dataframe columns
        def canonical(col_name: str) -> str:
            if col_name is None:
                return ""
            # normalize similar to mapping normalization
            s = str(col_name)
            s = re.sub(r"\(.*?\)", "", s)
            s = s.replace('\r', ' ').replace('\n', ' ').replace('/', ' ').replace('-', ' ')
            s = re.sub(r"[^0-9a-zA-Z ]+", "", s)
            s = re.sub(r"\s+", " ", s).strip().lower()
            return s

        ccp_candidates = {canonical(c): c for c in self.ccp_combined.columns}
        at_candidates = {canonical(c): c for c in self.at.columns}

        # Helper to find best match in normalized candidate keys
        def find_best_norm(norm_name, candidates_map, cutoff=0.6):
            if not norm_name:
                return None
            if norm_name in candidates_map:
                return candidates_map[norm_name]
            try:
                matches = difflib.get_close_matches(norm_name, list(candidates_map.keys()), n=1, cutoff=cutoff)
                return candidates_map[matches[0]] if matches else None
            except Exception:
                return None

        # Reset effective mappings list
        self.effective_mappings = []

        for _, row in self.mapping.iterrows():
            raw_ccp = row.get("ccp_column_raw", "")
            raw_at = row.get("at_column_raw", "")
            norm_ccp = row.get("ccp_column_norm", "")
            norm_at = row.get("at_column_norm", "")

            # Attempt to resolve normalized names to actual dataframe columns
            resolved_ccp = find_best_norm(norm_ccp, ccp_candidates)
            resolved_at = find_best_norm(norm_at, at_candidates) if norm_at else ""

            if resolved_ccp is None and norm_ccp:
                logger.debug(f"Mapping: could not resolve CCP '{raw_ccp}' (norm='{norm_ccp}') to available columns")
            if norm_at and not resolved_at:
                logger.debug(f"Mapping: could not resolve AT '{raw_at}' (norm='{norm_at}') to available columns")
            
            # Skip CCP-only fields (empty AT column)
            # Use resolved names
            ccp_col = resolved_ccp if resolved_ccp is not None else raw_ccp
            at_col = resolved_at if resolved_at is not None else (raw_at if raw_at else "")

            if not at_col:
                if ccp_col in self.ccp_combined.columns:
                    aligned_ccp[f"ccp_only_{ccp_col}"] = self.ccp_combined[ccp_col]
                else:
                    logger.debug(f"CCP-only mapping specified but CCP column '{ccp_col}' not found")
                # still record mapping for traceability (ccp -> '')
                self.effective_mappings.append((ccp_col, ""))
                continue

            # Normal mapping: prefer ccp_col if present, otherwise try to use mapped at_col if that exists in ccp_combined
            if ccp_col in self.ccp_combined.columns:
                aligned_ccp[at_col] = self.ccp_combined[ccp_col]
            elif at_col in self.ccp_combined.columns:
                aligned_ccp[at_col] = self.ccp_combined[at_col]
            else:
                aligned_ccp[at_col] = np.nan

            # record the effective mapping (resolved CCP column name, AT column name)
            self.effective_mappings.append((ccp_col, at_col))
        
        self.ccp_combined = aligned_ccp
    
    # ================================
    # STEP 9: RUN REQUIREMENTS
    # ================================
    
    def _run_requirements(self):
        """Run all three requirements"""
        ccp_keys = set(self.ccp_combined["composite_key"])
        at_keys = set(self.at["composite_key"])
        
        # Requirement 1: CCP not in AT
        req1_keys = ccp_keys - at_keys
        requirement_1 = self.ccp_combined[self.ccp_combined["composite_key"].isin(req1_keys)].copy()
        requirement_1["action"] = "ADD to AT Asia Whitelist"
        requirement_1 = requirement_1.drop(columns=["composite_key"])
        
        # Requirement 2: AT not in CCP
        req2_keys = at_keys - ccp_keys
        requirement_2 = self.at[self.at["composite_key"].isin(req2_keys)].copy()
        requirement_2["action"] = "REVIEW: Check activity/positions - DELETE or ADD to Exception List"
        requirement_2 = requirement_2.drop(columns=["composite_key"])
        
        # Requirement 3: Config mismatches
        common_keys = ccp_keys & at_keys
        requirement_3_list = []
        
        # Use effective resolved mappings if available (resolved to actual dataframe column names)
        if hasattr(self, 'effective_mappings') and len(self.effective_mappings) > 0:
            mapped_cols = self.effective_mappings
        else:
            mapped_cols = self.mapping[self.mapping["at_column"] != ""][['ccp_column', 'at_column']].values
        
        ccp_by_key = {key: self.ccp_combined[self.ccp_combined["composite_key"] == key].iloc[0] for key in common_keys}
        at_by_key = {key: self.at[self.at["composite_key"] == key].iloc[0] for key in common_keys}
        
        for key in common_keys:
            ccp_row = ccp_by_key[key]
            at_row = at_by_key[key]

            mismatches = []

            # If the mapping file has mappings, use them; otherwise derive common columns
            if len(mapped_cols) == 0:
                # derive columns to compare: intersection of at and ccp columns excluding keys
                compare_cols = [col for col in at_row.index if col not in (self.at_symbol_col, 'exchange', 'composite_key')]
                derived_mapped = [(col, col) for col in compare_cols if col in ccp_row.index]
                cols_to_compare = derived_mapped
            else:
                cols_to_compare = mapped_cols

            for ccp_col, at_col in cols_to_compare:
                # Determine AT value
                at_val = at_row[at_col] if at_col in at_row.index else np.nan

                # Determine CCP value from aligned CCP row:
                # - If alignment mapped CCP column into the AT column name, use that: ccp_row[at_col]
                # - Else if the original CCP-only field was preserved as 'ccp_only_{ccp_col}', use that
                # - Otherwise treat as missing
                if at_col in ccp_row.index:
                    ccp_val = ccp_row[at_col]
                elif f"ccp_only_{ccp_col}" in ccp_row.index:
                    ccp_val = ccp_row[f"ccp_only_{ccp_col}"]
                else:
                    ccp_val = np.nan

                if pd.isna(ccp_val) and pd.isna(at_val):
                    continue
                elif pd.isna(ccp_val) or pd.isna(at_val):
                    mismatches.append(f"{at_col} (CCP: {ccp_val}, AT: {at_val})")
                else:
                    # Compare as strings case-insensitive for robust matching
                    try:
                        if str(ccp_val).strip().lower() != str(at_val).strip().lower():
                            mismatches.append(f"{at_col} (CCP: {ccp_val}, AT: {at_val})")
                    except Exception:
                        if ccp_val != at_val:
                            mismatches.append(f"{at_col} (CCP: {ccp_val}, AT: {at_val})")

            if mismatches:
                # Build a combined record containing AT and CCP columns prefixed for side-by-side review
                combined = {}
                # add symbol and exchange explicitly
                combined[self.at_symbol_col] = at_row.get(self.at_symbol_col, '')
                combined['exchange'] = at_row.get('exchange', '')

                # AT-prefixed columns
                for col in at_row.index:
                    if col in (self.at_symbol_col, 'exchange', 'composite_key'):
                        continue
                    combined[f"at_{col}"] = at_row[col]

                # CCP-prefixed columns (use ccp_combined values which are aligned)
                for col in ccp_row.index:
                    if col in (self.at_symbol_col, 'exchange', 'composite_key'):
                        continue
                    combined[f"ccp_{col}"] = ccp_row[col]

                combined['mismatched_fields'] = "; ".join(mismatches)
                combined['action'] = "UPDATE AT to match CCP and SETUP Market Exception rule in CCP"

                requirement_3_list.append(combined)
        
        requirement_3 = pd.DataFrame(requirement_3_list)
        logger.info(f"Requirement 3 mismatches found: {len(requirement_3)}")

        return {
            'requirement_1': requirement_1,
            'requirement_2': requirement_2,
            'requirement_3': requirement_3
        }
    
    # ================================
    # STEP 10: GENERATE STATISTICS
    # ================================
    
    def _generate_statistics(self, results):
        """Generate comparison statistics"""
        ccp_keys = set(self.ccp_combined["composite_key"])
        at_keys = set(self.at["composite_key"])
        common_keys = ccp_keys & at_keys
        
        return {
            'total_ccp': len(self.ccp_combined),
            'total_at': len(self.at),
            'total_common': len(common_keys),
            'requirement_1_count': len(results['requirement_1']),
            'requirement_2_count': len(results['requirement_2']),
            'requirement_3_count': len(results['requirement_3']),
            'total_action_required': len(results['requirement_1']) + len(results['requirement_2']) + len(results['requirement_3']),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
