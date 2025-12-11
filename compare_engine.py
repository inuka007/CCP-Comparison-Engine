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

# Import column mappings from hardcoded configuration
from column_mappings import (
    get_mapped_columns,
    get_excluded_columns,
    should_compare_column,
    COLUMN_MAPPINGS
)

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
            
            # Validate required files loaded
            if self.ccp_sec is None or self.ccp_rules is None or self.at is None:
                raise ValidationError("Not all required files were found or loaded")
            
            logger.info("Files loaded successfully")
        
        except Exception as e:
            logger.error(f"Error loading files: {str(e)}")
            raise ValidationError(f"Error loading files: {str(e)}")
    
    # ================================
    # STEP 2: NORMALIZE COLUMNS
    # ================================
    
    def _normalize_columns(self):
        """Normalize column names across all dataframes"""
        for df in [self.ccp_sec, self.ccp_rules, self.at]:
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
            'at': ['exchange']
        }
        
        dfs = {
            'ccp_sec': self.ccp_sec,
            'ccp_rules': self.ccp_rules,
            'at': self.at
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
        """Prepare mapping - now using hardcoded mappings from column_mappings.py"""
        logger.info("Using hardcoded column mappings from column_mappings.py")
        
        # Use hardcoded mappings instead of reading from file
        # This ensures consistent column matching across all runs
        self.effective_mappings = get_mapped_columns()
        
        if not self.effective_mappings:
            logger.warning("No column mappings defined in column_mappings.py. Will auto-detect common columns.")
        else:
            logger.info(f"Loaded {len(self.effective_mappings)} column mappings")
    
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
        """Align CCP columns to AT structure using hardcoded mappings"""
        aligned_ccp = pd.DataFrame()
        aligned_ccp[self.at_symbol_col] = self.ccp_combined[self.ccp_symbol_col]
        aligned_ccp["exchange"] = self.ccp_combined["exchange"]
        aligned_ccp["composite_key"] = self.ccp_combined["composite_key"]
        
        # Use hardcoded mappings from column_mappings.py
        mapped_cols = COLUMN_MAPPINGS
        
        # Reset effective mappings list
        self.effective_mappings = []

        for ccp_col_original, at_col_original in mapped_cols.items():
            # Skip CCP-only fields (empty AT column)
            if not at_col_original or at_col_original == "":
                if ccp_col_original in self.ccp_combined.columns:
                    aligned_ccp[f"ccp_only_{ccp_col_original}"] = self.ccp_combined[ccp_col_original]
                self.effective_mappings.append((ccp_col_original, ""))
                continue

            # Normal mapping: use the CCP column if it exists
            if ccp_col_original in self.ccp_combined.columns:
                aligned_ccp[at_col_original] = self.ccp_combined[ccp_col_original]
            elif at_col_original in self.ccp_combined.columns:
                aligned_ccp[at_col_original] = self.ccp_combined[at_col_original]
            else:
                aligned_ccp[at_col_original] = np.nan

            # record the effective mapping
            self.effective_mappings.append((ccp_col_original, at_col_original))
        
        self.ccp_combined = aligned_ccp
    
    # ================================
    # STEP 9: RUN REQUIREMENTS
    # ================================
    
    def _normalize_boolean_value(self, val):
        """Normalize boolean-like values: YES/NO, TRUE/FALSE"""
        if pd.isna(val):
            return None
        val_str = str(val).strip().lower()
        if val_str in ['yes', 'true', '1']:
            return 'TRUE'
        elif val_str in ['no', 'false', '0']:
            return 'FALSE'
        return str(val).strip()
    
    def _values_match(self, ccp_val, at_val):
        """Compare two values considering boolean equivalences"""
        if pd.isna(ccp_val) and pd.isna(at_val):
            return True
        if pd.isna(ccp_val) or pd.isna(at_val):
            return False
        
        # Normalize both values
        ccp_norm = self._normalize_boolean_value(ccp_val)
        at_norm = self._normalize_boolean_value(at_val)
        
        # Compare normalized values
        return str(ccp_norm).lower() == str(at_norm).lower()
    
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
        
        # Columns to exclude from comparison (from column_mappings.py)
        at_exclude_cols = get_excluded_columns()
        at_exclude_cols.update({self.at_symbol_col, 'exchange', 'composite_key'})
        
        # Requirement 3: Config mismatches
        common_keys = ccp_keys & at_keys
        requirement_3_list = []
        
        # Use hardcoded mappings from column_mappings.py
        mapped_cols = get_mapped_columns()
        
        ccp_by_key = {key: self.ccp_combined[self.ccp_combined["composite_key"] == key].iloc[0] for key in common_keys}
        at_by_key = {key: self.at[self.at["composite_key"] == key].iloc[0] for key in common_keys}
        
        for key in common_keys:
            ccp_row = ccp_by_key[key]
            at_row = at_by_key[key]

            mismatched_field_names = []  # Track only column names with mismatches

            # Build the list of columns to compare based on hardcoded mappings
            # Only compare columns that exist in AT (i.e., have an AT equivalent in the mapping)
            cols_to_compare = []
            
            if mapped_cols:
                # Use hardcoded mapped columns - only those with AT equivalents
                for ccp_col, at_col in mapped_cols:
                    # Skip if AT column is empty (CCP-only field)
                    if not at_col or at_col == "":
                        continue
                    # Skip excluded AT columns
                    if at_col.lower() in at_exclude_cols:
                        continue
                    cols_to_compare.append((ccp_col, at_col))
            else:
                # Fallback: If no hardcoded mappings, compare columns that exist in both AT and CCP
                logger.warning("No column mappings found in column_mappings.py. Using auto-detection.")
                base_cols = {self.at_symbol_col, 'exchange', 'composite_key'}
                at_compare_cols = [col for col in at_row.index 
                                  if col.lower() not in at_exclude_cols and col not in base_cols]
                ccp_compare_cols = [col for col in ccp_row.index 
                                   if col.lower() not in at_exclude_cols and col not in base_cols]
                
                # Only pairs that exist in both
                common_cols = [col for col in at_compare_cols if col in ccp_compare_cols]
                cols_to_compare = [(col, col) for col in common_cols]

            # Now compare the columns
            for ccp_col, at_col in cols_to_compare:
                # Determine AT value
                at_val = at_row[at_col] if at_col in at_row.index else np.nan

                # Determine CCP value from aligned CCP row
                if at_col in ccp_row.index:
                    ccp_val = ccp_row[at_col]
                elif f"ccp_only_{ccp_col}" in ccp_row.index:
                    ccp_val = ccp_row[f"ccp_only_{ccp_col}"]
                else:
                    ccp_val = np.nan

                # Check if values match (considering boolean equivalences)
                if not self._values_match(ccp_val, at_val):
                    mismatched_field_names.append(at_col)

            if mismatched_field_names:
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

                # Only include the mismatched field column names
                combined['mismatched_fields'] = ", ".join(mismatched_field_names)
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
