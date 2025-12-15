"""
Requirements Analyzer Module

Performs the three requirements analysis:
1. Securities in CCP but not in AT
2. Securities in AT but not in CCP
3. Securities in both but with configuration mismatches
"""

import pandas as pd
import numpy as np
import logging

from column_mappings import (
    get_mapped_columns,
    get_excluded_columns
)

logger = logging.getLogger(__name__)


class RequirementsAnalyzer:
    """Analyzes three requirements for CCP vs AT comparison"""
    
    def __init__(self, ccp_combined_df, at_df, ccp_symbol_col, at_symbol_col):
        """
        Initialize requirements analyzer
        
        Args:
            ccp_combined_df: Combined CCP dataframe (Security + Market Rules)
            at_df: AT Whitelist dataframe
            ccp_symbol_col: Symbol column name in CCP
            at_symbol_col: Symbol column name in AT
        """
        self.ccp_combined = ccp_combined_df.copy()
        self.at = at_df.copy()
        self.ccp_symbol_col = ccp_symbol_col
        self.at_symbol_col = at_symbol_col
    
    def analyze(self):
        """
        Run all three requirements analysis
        
        Returns:
            dict: Dictionary with requirement_1, requirement_2, requirement_3, requirement_3_pivot dataframes
        """
        logger.info("Starting requirements analysis...")
        
        # Extract composite keys
        ccp_keys = set(self.ccp_combined["composite_key"])
        at_keys = set(self.at["composite_key"])
        
        # Requirement 1: Securities in CCP but not in AT
        logger.info("Analyzing Requirement 1: CCP securities not in AT...")
        requirement_1 = self._analyze_requirement_1(ccp_keys, at_keys)
        
        # Requirement 2: Securities in AT but not in CCP
        logger.info("Analyzing Requirement 2: AT securities not in CCP...")
        requirement_2 = self._analyze_requirement_2(ccp_keys, at_keys)
        
        # Requirement 3: Configuration mismatches
        logger.info("Analyzing Requirement 3: Configuration mismatches...")
        requirement_3, requirement_3_pivot = self._analyze_requirement_3(ccp_keys, at_keys)
        
        logger.info("Requirements analysis completed")
        
        return {
            'requirement_1': requirement_1,
            'requirement_2': requirement_2,
            'requirement_3': requirement_3,
            'requirement_3_pivot': requirement_3_pivot,
            'ccp_keys': ccp_keys,
            'at_keys': at_keys
        }
    
    def _analyze_requirement_1(self, ccp_keys, at_keys):
        """
        Requirement 1: Securities in CCP but not in AT
        Action: ADD to AT Asia Whitelist
        """
        req1_keys = ccp_keys - at_keys
        requirement_1 = self.ccp_combined[
            self.ccp_combined["composite_key"].isin(req1_keys)
        ].copy()
        
        requirement_1["action"] = "ADD to AT Asia Whitelist"
        requirement_1 = requirement_1.drop(columns=["composite_key"])
        
        logger.info(f"Requirement 1 count: {len(requirement_1)}")
        return requirement_1
    
    def _analyze_requirement_2(self, ccp_keys, at_keys):
        """
        Requirement 2: Securities in AT but not in CCP
        Action: REVIEW - Check activity/positions, DELETE or ADD to Exception List
        """
        req2_keys = at_keys - ccp_keys
        requirement_2 = self.at[self.at["composite_key"].isin(req2_keys)].copy()
        
        requirement_2["action"] = "REVIEW: Check activity/positions - DELETE or ADD to Exception List"
        requirement_2 = requirement_2.drop(columns=["composite_key"])
        
        logger.info(f"Requirement 2 count: {len(requirement_2)}")
        return requirement_2
    
    def _analyze_requirement_3(self, ccp_keys, at_keys):
        """
        Requirement 3: Securities in both CCP and AT but with configuration mismatches
        
        Only compares columns that have AT equivalents (based on column_mappings)
        Excludes audit/admin columns
        """
        requirement_3_list = []
        common_keys = ccp_keys & at_keys
        
        # Get excluded columns
        at_exclude_cols = get_excluded_columns()
        at_exclude_cols.update({self.at_symbol_col, 'exchange', 'composite_key'})
        
        # Get mapped columns for comparison
        mapped_cols = get_mapped_columns()
        
        # Build lookup dictionaries for fast access
        ccp_by_key = {
            key: self.ccp_combined[self.ccp_combined["composite_key"] == key].iloc[0] 
            for key in common_keys
        }
        at_by_key = {
            key: self.at[self.at["composite_key"] == key].iloc[0] 
            for key in common_keys
        }
        
        # Compare each common record
        for key in common_keys:
            ccp_row = ccp_by_key[key]
            at_row = at_by_key[key]
            
            mismatched_field_names = self._find_mismatches(
                ccp_row, at_row, mapped_cols, at_exclude_cols
            )
            
            if mismatched_field_names:
                combined = self._build_requirement_3_record(
                    ccp_row, at_row, mismatched_field_names
                )
                requirement_3_list.append(combined)
        
        requirement_3 = pd.DataFrame(requirement_3_list)
        logger.info(f"Requirement 3 count: {len(requirement_3)}")
        
        # Generate pivot summary for mismatch analysis
        pivot_summary = self._generate_pivot_summary(requirement_3)
        
        return requirement_3, pivot_summary
    
    def _find_mismatches(self, ccp_row, at_row, mapped_cols, at_exclude_cols):
        """
        Find mismatched fields between CCP and AT rows
        
        Only compares columns that:
        1. Have AT equivalents (defined in mappings)
        2. Actually exist in both rows
        3. Are not in the exclude list
        """
        mismatched_field_names = []
        
        # Determine columns to compare
        if mapped_cols:
            cols_to_compare = [
                (ccp_col, at_col) for ccp_col, at_col in mapped_cols
                if at_col and at_col != "" and at_col.lower() not in at_exclude_cols
            ]
        else:
            # Fallback: auto-detect common columns
            logger.warning("No column mappings found. Using auto-detection.")
            base_cols = {self.at_symbol_col, 'exchange', 'composite_key'}
            at_cols = [c for c in at_row.index if c.lower() not in at_exclude_cols and c not in base_cols]
            ccp_cols = [c for c in ccp_row.index if c.lower() not in at_exclude_cols and c not in base_cols]
            common = [c for c in at_cols if c in ccp_cols]
            cols_to_compare = [(c, c) for c in common]
        
        # Compare each column pair - only if column actually exists in both rows
        for ccp_col, at_col in cols_to_compare:
            # Check if AT column exists in AT row
            if at_col not in at_row.index:
                continue
            
            # Check if we can find the CCP value
            if at_col in ccp_row.index:
                ccp_val = ccp_row[at_col]
            elif ccp_col in ccp_row.index:
                ccp_val = ccp_row[ccp_col]
            else:
                # Column doesn't exist in CCP row, skip comparison
                continue
            
            at_val = at_row[at_col]
            
            # Compare values
            if not self._values_match(ccp_val, at_val):
                mismatched_field_names.append(at_col)
        
        return mismatched_field_names
    
    def _values_match(self, ccp_val, at_val):
        """
        Compare two values with proper type handling
        
        Mappings:
        - TRUE = YES (case-insensitive)
        - FALSE = NO (case-insensitive)
        - Numeric values (including 0, 1, etc.) are compared as exact numeric/string values
        - NaN/None are treated as equal to each other
        """
        # Handle NaN/None cases
        ccp_is_na = pd.isna(ccp_val)
        at_is_na = pd.isna(at_val)
        
        if ccp_is_na and at_is_na:
            return True
        if ccp_is_na or at_is_na:
            return False
        
        # Convert to strings for comparison
        ccp_str = str(ccp_val).strip().upper()
        at_str = str(at_val).strip().upper()
        
        # Apply boolean text mappings only for explicit text boolean values
        # TRUE should equal YES, FALSE should equal NO
        ccp_normalized = self._normalize_boolean_text(ccp_str)
        at_normalized = self._normalize_boolean_text(at_str)
        
        # Compare normalized values
        return ccp_normalized == at_normalized
    
    def _normalize_boolean_text(self, val_str):
        """
        Normalize only explicit boolean text values
        
        TRUE -> TRUE
        YES -> TRUE
        FALSE -> FALSE
        NO -> FALSE
        Everything else (including 0, 1, numeric values) -> returned as-is
        """
        if val_str == 'TRUE':
            return 'TRUE'
        elif val_str == 'YES':
            return 'TRUE'
        elif val_str == 'FALSE':
            return 'FALSE'
        elif val_str == 'NO':
            return 'FALSE'
        else:
            # Return numeric and other values as-is
            return val_str
    
    def _build_requirement_3_record(self, ccp_row, at_row, mismatched_fields):
        """
        Build a single Requirement 3 record for output
        
        Includes symbol, exchange, prefixed AT/CCP columns, and mismatched field names
        """
        combined = {}
        
        # Add key identifiers
        combined[self.at_symbol_col] = at_row.get(self.at_symbol_col, '')
        combined['exchange'] = at_row.get('exchange', '')
        
        # Add AT-prefixed columns
        for col in at_row.index:
            if col not in (self.at_symbol_col, 'exchange', 'composite_key'):
                combined[f"at_{col}"] = at_row[col]
        
        # Add CCP-prefixed columns
        for col in ccp_row.index:
            if col not in (self.at_symbol_col, 'exchange', 'composite_key'):
                combined[f"ccp_{col}"] = ccp_row[col]
        
        # Add mismatched field names and action
        combined['mismatched_fields'] = ", ".join(mismatched_fields)
        combined['action'] = "UPDATE AT to match CCP and SETUP Market Exception rule in CCP"
        
        return combined
    
    def _generate_pivot_summary(self, requirement_3_df):
        """
        Generate pivot summary: column headers as rows, exchanges as columns, mismatch counts as values
        
        Returns a DataFrame with column headers as index and exchanges as columns
        """
        if requirement_3_df.empty:
            return pd.DataFrame()
        
        # Extract mismatched fields and split into individual columns
        mismatch_records = []
        for _, row in requirement_3_df.iterrows():
            exchange = row['exchange']
            mismatched_fields = row.get('mismatched_fields', '')
            
            if pd.notna(mismatched_fields) and mismatched_fields:
                # Split by comma and strip whitespace
                fields = [f.strip() for f in str(mismatched_fields).split(',')]
                for field in fields:
                    if field:  # Ignore empty strings
                        mismatch_records.append({
                            'exchange': exchange,
                            'column_header': field
                        })
        
        if not mismatch_records:
            return pd.DataFrame()
        
        # Create DataFrame from records
        mismatch_df = pd.DataFrame(mismatch_records)
        
        # Create pivot table: column_header × exchange → count
        pivot = pd.pivot_table(
            mismatch_df,
            index='column_header',
            columns='exchange',
            aggfunc='size',
            fill_value=0
        )
        
        # Sort by total mismatches descending
        pivot['Total'] = pivot.sum(axis=1)
        pivot = pivot.sort_values('Total', ascending=False)
        
        logger.info(f"Pivot summary generated: {len(pivot)} unique mismatched columns across {len(pivot.columns)-1} exchanges")
        return pivot
