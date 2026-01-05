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

from mappings.column_mappings import (
    get_mapped_columns,
    get_excluded_columns
)
from mappings.segment_mapping import classify_security

logger = logging.getLogger(__name__)


class RequirementsAnalyzer:
    """Analyzes three requirements for CCP vs AT comparison"""
    
    def __init__(self, ccp_combined_df, at_df, ccp_symbol_col, at_symbol_col, dbeaver_df=None):
        """
        Initialize requirements analyzer
        
        Args:
            ccp_combined_df: Combined CCP dataframe (Security + Market Rules)
            at_df: AT Whitelist dataframe
            ccp_symbol_col: Symbol column name in CCP
            at_symbol_col: Symbol column name in AT
            dbeaver_df: DBeaver Results dataframe (optional)
        """
        self.ccp_combined = ccp_combined_df.copy()
        self.at = at_df.copy()
        self.ccp_symbol_col = ccp_symbol_col
        self.at_symbol_col = at_symbol_col
        self.dbeaver = dbeaver_df.copy() if dbeaver_df is not None else None
    
    def analyze(self):
        """
        Run all three requirements analysis
        
        Returns:
            dict: Dictionary with requirement_1, requirement_2, requirement_3, requirement_3_pivot, 
                  requirement_1_pivot dataframes
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
        
        # Enrich Requirement 2 with DBeaver data and generate summary
        requirement_2_pivot = self._generate_requirement_2_summary(requirement_2)
        
        # Requirement 3: Configuration mismatches
        logger.info("Analyzing Requirement 3: Configuration mismatches...")
        requirement_3, requirement_3_pivot = self._analyze_requirement_3(ccp_keys, at_keys)
        
        # Generate segment-wise summary for Requirement 1
        requirement_1_pivot = self._generate_requirement_1_summary(requirement_1)
        
        logger.info("Requirements analysis completed")
        
        return {
            'requirement_1': requirement_1,
            'requirement_1_pivot': requirement_1_pivot,
            'requirement_2': requirement_2,
            'requirement_2_pivot': requirement_2_pivot,
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
        
        Enriches with DBeaver data (tcl1_desc, tcl2_desc, tcl3_desc) if available
        """
        req2_keys = at_keys - ccp_keys
        requirement_2 = self.at[self.at["composite_key"].isin(req2_keys)].copy()
        
        # Enrich with DBeaver data if available
        if self.dbeaver is not None:
            logger.info("Enriching Requirement 2 with DBeaver data...")
            
            # Normalize DBeaver columns for matching
            dbeaver_enriched = self.dbeaver.copy()
            
            # Create symbol and exchange columns in DBeaver if they have different names
            # ticker_id -> symbol, source_id -> exchange
            if 'ticker_id' in dbeaver_enriched.columns:
                dbeaver_enriched['symbol'] = dbeaver_enriched['ticker_id']
            if 'source_id' in dbeaver_enriched.columns:
                dbeaver_enriched['exchange'] = dbeaver_enriched['source_id']
            
            # Normalize for matching
            if 'symbol' in dbeaver_enriched.columns and 'exchange' in dbeaver_enriched.columns:
                dbeaver_enriched['symbol'] = dbeaver_enriched['symbol'].astype(str).str.strip().str.upper()
                dbeaver_enriched['exchange'] = dbeaver_enriched['exchange'].astype(str).str.strip().str.upper()
                
                # Select relevant columns for enrichment
                enrich_cols = ['symbol', 'exchange']
                for col in ['tcl1_desc', 'tcl2_desc', 'tcl3_desc']:
                    if col in dbeaver_enriched.columns:
                        enrich_cols.append(col)
                
                dbeaver_subset = dbeaver_enriched[enrich_cols].drop_duplicates()
                
                # Merge with requirement_2
                requirement_2 = requirement_2.merge(
                    dbeaver_subset,
                    on=['symbol', 'exchange'],
                    how='left'
                )
                logger.info(f"Enriched {len(requirement_2)} Requirement 2 records with DBeaver data")
        
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
    def _generate_requirement_1_summary(self, requirement_1_df):
        """
        Generate segment-wise summary for Requirement 1 (CCP securities not in AT)
        
        Creates a pivot table with segments as rows and columns showing:
        - CCP # Securities (count of securities in CCP for that segment)
        - AT ASIA # Securities (always 0 for Req1 since they're not in AT)
        - Difference (negative of CCP count)
        
        Returns a DataFrame with segment names as index
        """
        if requirement_1_df.empty:
            # Return empty dataframe with proper structure
            return pd.DataFrame({
                'Segment Name': [],
                'CCP # Securities': []
            })
        
        # Log available columns for debugging
        logger.info(f"Requirement 1 columns: {list(requirement_1_df.columns)}")
        
        # Build segment classification for each row
        segment_records = []
        for _, row in requirement_1_df.iterrows():
            exchange = row.get('exchange', '')
            tcl1_value = row.get('ccp_only_tcl1', '')
            
            # Log first few records for debugging
            if len(segment_records) < 5:
                logger.info(f"Row: exchange={exchange}, tcl1={tcl1_value}")
            
            segment_name = classify_security(exchange, tcl1_value)
            if segment_name:
                segment_records.append({
                    'segment_name': segment_name,
                    'symbol': row.get(self.ccp_symbol_col, '')
                })
                if len(segment_records) <= 5:
                    logger.info(f"  -> Classified as: {segment_name}")
        
        if not segment_records:
            return pd.DataFrame()
        
        # Create dataframe from records
        segment_df = pd.DataFrame(segment_records)
        
        # Count securities per segment
        segment_counts = segment_df.groupby('segment_name').size().reset_index(name='count')
        
        # Define segment order for consistent display
        segment_order = [
            'US EQUITY', 'EUROPEAN EQUITY', 'ASIA EQUITY',
            'US ETP', 'EUROPEAN ETP', 'ASIA ETP'
        ]
        
        # Create summary dataframe with all segments
        summary_records = []
        for segment in segment_order:
            count = segment_counts[segment_counts['segment_name'] == segment]['count'].sum()
            if count > 0 or segment in segment_counts['segment_name'].values:
                summary_records.append({
                    'Segment Name': segment,
                    'CCP # Securities': int(count) if count > 0 else 0,
                    'AT ASIA # Securities': 0,  # Always 0 for Req1
                    'Difference': -int(count) if count > 0 else 0
                })
        
        if not summary_records:
            return pd.DataFrame()
        
        summary_df = pd.DataFrame(summary_records)
        
        # Remove AT and Difference columns - only show CCP count
        summary_df = summary_df[['Segment Name', 'CCP # Securities']]
        
        # Add total row
        total_row = pd.DataFrame([{
            'Segment Name': 'Total # Securities',
            'CCP # Securities': summary_df['CCP # Securities'].sum()
        }])
        
        summary_df = pd.concat([summary_df, total_row], ignore_index=True)
        
        logger.info(f"Requirement 1 summary generated: {len(summary_df)-1} segments")
        return summary_df
    def _generate_requirement_2_summary(self, requirement_2_df):
        """
        Generate region/product category summary for Requirement 2 (AT securities not in CCP)
        
        Creates separate summaries for each region based on tcl1_desc, tcl2_desc, tcl3_desc from DBeaver data
        Also generates an overall summary showing comparable vs uncomparable records per region
        
        Returns a dict with:
        - 'regional_summaries': {region_name: DataFrame} with TCL breakdown per region
        - 'overall_summary': DataFrame with comparable/uncomparable counts per region
        """
        if requirement_2_df.empty:
            return {
                'regional_summaries': {},
                'overall_summary': pd.DataFrame()
            }
        
        # Check if DBeaver enrichment columns are available
        if 'tcl1_desc' not in requirement_2_df.columns:
            logger.warning("DBeaver data not available for Requirement 2 summary")
            return {
                'regional_summaries': {},
                'overall_summary': pd.DataFrame()
            }
        
        # Map exchanges to regions
        from mappings.segment_mapping import get_region_for_exchange
        
        # Add region column
        requirement_2_df['region'] = requirement_2_df['exchange'].apply(
            lambda x: get_region_for_exchange(x) or 'Unknown'
        )
        
        # Map region names for display
        region_display_map = {
            'US': 'Americas',
            'EUROPE': 'Europe',
            'ASIA': 'Asia',
            'Unknown': 'Unknown'
        }
        requirement_2_df['region_display'] = requirement_2_df['region'].map(
            lambda x: region_display_map.get(x, x)
        )
        
        # Identify comparable vs uncomparable records
        # Uncomparable = records where all TCL fields are missing/null
        requirement_2_df['is_comparable'] = ~(
            requirement_2_df['tcl1_desc'].isna() & 
            requirement_2_df['tcl2_desc'].isna() & 
            requirement_2_df['tcl3_desc'].isna()
        )
        
        # Generate Overall Summary
        overall_records = []
        region_order = ['Americas', 'Asia', 'Europe', 'Unknown']
        
        for region in region_order:
            region_df = requirement_2_df[requirement_2_df['region_display'] == region]
            if region_df.empty:
                continue
                
            total_count = len(region_df)
            comparable_count = region_df['is_comparable'].sum()
            uncomparable_count = total_count - comparable_count
            
            overall_records.append({
                'Region': region,
                'In AT not CCP': int(total_count),
                'Exist in Product DB': int(comparable_count),
                'Do not exist in DB': int(uncomparable_count)
            })
        
        overall_summary = pd.DataFrame(overall_records) if overall_records else pd.DataFrame()
        
        # Add total row to overall summary
        if not overall_summary.empty:
            total_row = pd.DataFrame([{
                'Region': 'Total',
                'In AT not CCP': int(overall_summary['In AT not CCP'].sum()),
                'Exist in Product DB': int(overall_summary['Exist in Product DB'].sum()),
                'Do not exist in DB': int(overall_summary['Do not exist in DB'].sum())
            }])
            overall_summary = pd.concat([overall_summary, total_row], ignore_index=True)
        
        # Generate Regional Summaries (only for comparable records)
        comparable_df = requirement_2_df[requirement_2_df['is_comparable'] == True]
        
        # Create separate DataFrames per region
        # Each region will show unique values for each TCL level with counts
        region_summaries = {}
        
        for region in region_order:
            region_df = comparable_df[comparable_df['region_display'] == region]
            
            if region_df.empty:
                continue
            
            # Build summary with unique values for each TCL level
            summary_records = []
            
            # Count unique TCL1 values
            tcl1_counts = region_df['tcl1_desc'].value_counts()
            for tcl1_val, count in tcl1_counts.items():
                if pd.notna(tcl1_val):
                    summary_records.append({
                        'TCL1': tcl1_val,
                        'TCL2': '',
                        'TCL3': '',
                        'Count': int(count)
                    })
            
            # Count unique TCL2 values
            tcl2_counts = region_df['tcl2_desc'].value_counts()
            for tcl2_val, count in tcl2_counts.items():
                if pd.notna(tcl2_val):
                    summary_records.append({
                        'TCL1': '',
                        'TCL2': tcl2_val,
                        'TCL3': '',
                        'Count': int(count)
                    })
            
            # Count unique TCL3 values
            tcl3_counts = region_df['tcl3_desc'].value_counts()
            for tcl3_val, count in tcl3_counts.items():
                if pd.notna(tcl3_val):
                    summary_records.append({
                        'TCL1': '',
                        'TCL2': '',
                        'TCL3': tcl3_val,
                        'Count': int(count)
                    })
            
            if summary_records:
                summary_df = pd.DataFrame(summary_records)
                # Sort by count descending
                summary_df = summary_df.sort_values('Count', ascending=False)
                region_summaries[region] = summary_df
                logger.info(f"Requirement 2 summary for {region}: {len(summary_df)} TCL entries")
        
        logger.info(f"Overall summary: {len(overall_summary)-1 if not overall_summary.empty else 0} regions")
        
        return {
            'regional_summaries': region_summaries,
            'overall_summary': overall_summary
        }
