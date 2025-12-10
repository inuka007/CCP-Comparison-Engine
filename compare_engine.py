"""
Comparison Engine Module
Core logic for comparing CCP and AT whitelists
Refactored from compare_whitelists.py for use in GUI
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging

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
        
        self.mapping["ccp_column"] = self.mapping["ccp_column"].str.lower().str.strip()
        self.mapping["at_column"] = self.mapping["at_column"].str.lower().str.strip()
    
    # ================================
    # STEP 7: CREATE COMPOSITE KEYS
    # ================================
    
    def _create_composite_keys(self):
        """Create composite keys for comparison"""
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
        for _, row in self.mapping.iterrows():
            ccp_col = row["ccp_column"]
            at_col = row["at_column"]
            
            # Skip CCP-only fields (empty AT column)
            if at_col == "":
                if ccp_col in self.ccp_combined.columns:
                    aligned_ccp[f"ccp_only_{ccp_col}"] = self.ccp_combined[ccp_col]
                continue
            
            # Normal mapping
            if ccp_col in self.ccp_combined.columns:
                aligned_ccp[at_col] = self.ccp_combined[ccp_col]
            else:
                aligned_ccp[at_col] = np.nan
        
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
        
        mapped_cols = self.mapping[self.mapping["at_column"] != ""][["ccp_column", "at_column"]].values
        
        ccp_by_key = {key: self.ccp_combined[self.ccp_combined["composite_key"] == key].iloc[0] for key in common_keys}
        at_by_key = {key: self.at[self.at["composite_key"] == key].iloc[0] for key in common_keys}
        
        for key in common_keys:
            ccp_row = ccp_by_key[key]
            at_row = at_by_key[key]
            
            mismatches = []
            
            for ccp_col, at_col in mapped_cols:
                if ccp_col in ccp_row.index and at_col in at_row.index:
                    ccp_val = ccp_row[ccp_col]
                    at_val = at_row[at_col]
                    
                    if pd.isna(ccp_val) and pd.isna(at_val):
                        continue
                    elif pd.isna(ccp_val) or pd.isna(at_val):
                        mismatches.append(f"{at_col} (CCP: {ccp_val}, AT: {at_val})")
                    elif str(ccp_val).lower() != str(at_val).lower():
                        mismatches.append(f"{at_col} (CCP: {ccp_val}, AT: {at_val})")
            
            if mismatches:
                requirement_3_list.append({
                    self.at_symbol_col: ccp_row[self.at_symbol_col],
                    "exchange": ccp_row["exchange"],
                    "mismatched_fields": "; ".join(mismatches),
                    "action": "UPDATE AT to match CCP and SETUP Market Exception rule in CCP"
                })
        
        requirement_3 = pd.DataFrame(requirement_3_list)
        
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
