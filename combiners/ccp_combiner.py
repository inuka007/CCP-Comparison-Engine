"""
CCP Data Combiner Module

Combines CCP Security Whitelist and CCP Market Rules into a unified grid.
This module handles all CCP-specific data preparation and merging.
"""

import pandas as pd
import numpy as np
import logging

from mappings.segment_mapping import classify_security

logger = logging.getLogger(__name__)


class CCPCombiner:
    """Combines CCP Security Whitelist with CCP Market Rules"""
    
    def __init__(self, ccp_security_df, ccp_rules_df):
        """
        Initialize CCP combiner
        
        Args:
            ccp_security_df: CCP Security Whitelist dataframe (normalized columns)
            ccp_rules_df: CCP Market Rules dataframe (normalized columns)
        """
        self.ccp_sec = ccp_security_df.copy()
        self.ccp_rules = ccp_rules_df.copy()
        self.ccp_combined = None
        self.ccp_symbol_col = None
        self.ccp_duplicates = pd.DataFrame()  # Stores detected duplicates before removal
        
    def combine(self):
        """
        Combine CCP datasets
        
        Returns:
            CCPCombiner: self for method chaining
        """
        self._detect_symbol_column()
        self._detect_and_remove_duplicates()
        self._normalize_segment_values()
        self._merge_datasets()
        return self
    
    def _detect_and_remove_duplicates(self):
        """
        Detect and remove duplicate symbol/exchange entries in CCP Security Whitelist
        where one record has EXCEPTION_INCLUSION segment and another has a real segment.
        
        Logic:
        - Group by symbol + exchange
        - If a group has >1 row AND one of them is EXCEPTION_INCLUSION,
          remove the EXCEPTION_INCLUSION row and keep the other.
        - Store removed duplicates for UI display.
        """
        if 'segment' not in self.ccp_sec.columns:
            logger.info("No segment column, skipping duplicate detection")
            return
        
        symbol_col = self.ccp_symbol_col
        
        # Normalize for grouping (temporary uppercase copies)
        sym_upper = self.ccp_sec[symbol_col].astype(str).str.strip().str.upper()
        exch_upper = self.ccp_sec['exchange'].astype(str).str.strip().str.upper()
        seg_upper = self.ccp_sec['segment'].astype(str).str.strip().str.upper().str.replace(' ', '_')
        
        self.ccp_sec['_group_key'] = sym_upper + '|' + exch_upper
        self.ccp_sec['_seg_norm'] = seg_upper
        
        # Find groups with more than one row
        group_counts = self.ccp_sec.groupby('_group_key').size()
        dup_keys = group_counts[group_counts > 1].index.tolist()
        
        if not dup_keys:
            logger.info("No duplicate symbol/exchange entries found in CCP Security Whitelist")
            self.ccp_sec.drop(columns=['_group_key', '_seg_norm'], inplace=True)
            return
        
        logger.info(f"Found {len(dup_keys)} duplicate symbol/exchange groups in CCP Security Whitelist")
        
        rows_to_remove = []
        duplicate_records = []
        
        for key in dup_keys:
            group = self.ccp_sec[self.ccp_sec['_group_key'] == key]
            segments_in_group = group['_seg_norm'].tolist()
            
            # Check if EXCEPTION_INCLUSION is one of the segments
            if 'EXCEPTION_INCLUSION' not in segments_in_group:
                logger.info(f"Duplicate group {key} has no EXCEPTION_INCLUSION, skipping")
                continue
            
            # Get the non-EXCEPTION_INCLUSION rows and the EXCEPTION_INCLUSION rows
            exc_rows = group[group['_seg_norm'] == 'EXCEPTION_INCLUSION']
            non_exc_rows = group[group['_seg_norm'] != 'EXCEPTION_INCLUSION']
            
            if non_exc_rows.empty:
                # All duplicates are EXCEPTION_INCLUSION - skip, nothing to prefer
                logger.info(f"Duplicate group {key} has only EXCEPTION_INCLUSION rows, skipping")
                continue
            
            # Mark EXCEPTION_INCLUSION rows for removal
            kept_segments = non_exc_rows['segment'].tolist()
            for idx in exc_rows.index:
                rows_to_remove.append(idx)
                symbol = self.ccp_sec.at[idx, symbol_col]
                exchange = self.ccp_sec.at[idx, 'exchange']
                exc_segment = self.ccp_sec.at[idx, 'segment']
                
                # Store the full row data for export
                row_data = self.ccp_sec.loc[idx].to_dict()
                row_data['kept_segment'] = ', '.join(str(s) for s in kept_segments)
                duplicate_records.append(row_data)
                
                logger.info(
                    f"  Removing duplicate: {symbol}|{exchange} "
                    f"segment={exc_segment} (keeping {kept_segments})"
                )
        
        # Store duplicates info for UI display
        if duplicate_records:
            self.ccp_duplicates = pd.DataFrame(duplicate_records)
            logger.info(
                f"Removing {len(rows_to_remove)} EXCEPTION_INCLUSION duplicate rows "
                f"from CCP Security Whitelist"
            )
            self.ccp_sec.drop(index=rows_to_remove, inplace=True)
            self.ccp_sec.reset_index(drop=True, inplace=True)
        
        # Cleanup temp columns
        self.ccp_sec.drop(columns=['_group_key', '_seg_norm'], inplace=True)
    
    def get_duplicates(self):
        """
        Get the detected duplicate records that were removed.
        
        Returns:
            pd.DataFrame: DataFrame with all original CCP columns plus kept_segment
        """
        return self.ccp_duplicates

    def _normalize_segment_values(self):
        """
        Normalize merge key values (exchange, segment, mic_code) in both CCP
        Security Whitelist and Market Rules to uppercase, trimmed, with
        underscores for consistent matching.
        """
        for df_name, df in [('CCP Security', self.ccp_sec), ('CCP Rules', self.ccp_rules)]:
            # Normalize exchange values
            if 'exchange' in df.columns:
                df['exchange'] = df['exchange'].astype(str).str.strip().str.upper()
                logger.info(f"Normalized exchange values in {df_name}: {df['exchange'].unique().tolist()}")
            
            # Normalize segment values
            if 'segment' in df.columns:
                mask = df['segment'].notna()
                df.loc[mask, 'segment'] = (
                    df.loc[mask, 'segment']
                    .astype(str).str.strip().str.upper().str.replace(' ', '_')
                )
                logger.info(f"Normalized segment values in {df_name}: {df['segment'].unique().tolist()}")
            
            # Normalize mic_code values
            if 'mic_code' in df.columns:
                df['mic_code'] = df['mic_code'].astype(str).str.strip().str.upper()
                logger.info(f"Normalized mic_code values in {df_name}: {df['mic_code'].unique().tolist()}")
    
    def _reclassify_exception_inclusions(self):
        """
        Reclassify EXCEPTION_INCLUSION securities to their actual segment
        based on exchange and tcl1 (product type) using segment_mapping.
        
        EXCEPTION_INCLUSION securities are those added to CCP due to operational
        or management decisions. For comparison purposes, they need to be mapped
        to their actual segment (US_EQUITY, EUROPEAN_ETP, etc.) so the correct
        Market Rules are applied.
        """
        if 'segment' not in self.ccp_sec.columns:
            logger.warning("No 'segment' column in CCP Security Whitelist, skipping reclassification")
            return
        
        # Find EXCEPTION_INCLUSION rows
        mask = self.ccp_sec['segment'].astype(str).str.strip().str.upper() == 'EXCEPTION_INCLUSION'
        exception_count = mask.sum()
        
        if exception_count == 0:
            logger.info("No EXCEPTION_INCLUSION securities found")
            return
        
        logger.info(f"Reclassifying {exception_count} EXCEPTION_INCLUSION securities...")
        
        # Detect tcl1 column (product type indicator)
        tcl1_col = None
        for col in ['tcl1', 'tcl_1', 'traded_products']:
            if col in self.ccp_sec.columns:
                tcl1_col = col
                break
        
        reclassified_count = 0
        failed_count = 0
        for idx in self.ccp_sec[mask].index:
            exchange = self.ccp_sec.at[idx, 'exchange']
            tcl1_value = self.ccp_sec.at[idx, tcl1_col] if tcl1_col else None
            
            segment_name = classify_security(exchange, tcl1_value)
            if segment_name:
                # Convert "US EQUITY" -> "US_EQUITY" format to match CCP Market Rules
                self.ccp_sec.at[idx, 'segment'] = segment_name.replace(' ', '_')
                reclassified_count += 1
            else:
                failed_count += 1
                symbol = self.ccp_sec.at[idx, self.ccp_symbol_col] if self.ccp_symbol_col else 'Unknown'
                logger.warning(
                    f"Could not reclassify EXCEPTION_INCLUSION: {symbol} | exchange={exchange}"
                )
        
        logger.info(
            f"Reclassified {reclassified_count}/{exception_count} EXCEPTION_INCLUSION securities "
            f"({failed_count} could not be classified)"
        )

    def _detect_symbol_column(self):
        """Detect symbol column in CCP Security whitelist"""
        common_names = ['symbol', 'security_id', 'isin', 'cusip', 'identifier', 'secid']
        
        for col in common_names:
            if col in self.ccp_sec.columns:
                self.ccp_symbol_col = col
                logger.info(f"Detected symbol column in CCP: {col}")
                return
        
        raise ValueError(f"Could not detect symbol column in CCP. Available: {list(self.ccp_sec.columns)}")
    
    def _merge_datasets(self):
        """
        Merge CCP Security Whitelist with CCP Market Rules.
        
        MIC_CODE priority logic:
        - mic_code="ALL": rule applies to ALL securities in that exchange+segment
        - mic_code=<symbol>: rule applies ONLY to that symbol and overrides the
          "ALL" rule for that specific security.
        
        Steps:
        1. Split Market Rules into "ALL" rules and symbol-specific rules
        2. Merge ALL rules on ['exchange', 'segment'] (base rules for everyone)
        3. For symbol-specific rules, find matching securities by symbol+exchange+segment
           and override the base rule values
        4. Fallback for EXCEPTION_INCLUSION rows without rules
        
        Falls back to exchange-only merge if segment column is not available.
        """
        logger.info("Merging CCP Security Whitelist with CCP Market Rules...")
        
        # Determine merge keys based on available columns
        has_segment = (
            'segment' in self.ccp_sec.columns and 
            'segment' in self.ccp_rules.columns
        )
        merge_keys = ['exchange', 'segment'] if has_segment else ['exchange']
        logger.info(f"Merge keys: {merge_keys}")
        
        # --- Split rules by MIC_CODE ---
        has_mic_code = 'mic_code' in self.ccp_rules.columns
        if has_mic_code:
            all_rules = self.ccp_rules[self.ccp_rules['mic_code'] == 'ALL'].copy()
            symbol_rules = self.ccp_rules[self.ccp_rules['mic_code'] != 'ALL'].copy()
            logger.info(
                f"MIC_CODE split: {len(all_rules)} ALL rules, "
                f"{len(symbol_rules)} symbol-specific rules"
            )
        else:
            all_rules = self.ccp_rules.copy()
            symbol_rules = pd.DataFrame()
            logger.info("No mic_code column found, treating all rules as ALL")
        
        # --- Step 1: Deduplicate ALL rules ---
        if all(k in all_rules.columns for k in merge_keys):
            duplicates = all_rules.duplicated(subset=merge_keys).sum()
            if duplicates > 0:
                logger.warning(f"Found {duplicates} duplicate {merge_keys} entries in ALL rules")
                all_rules = all_rules.drop_duplicates(subset=merge_keys, keep='first')
                logger.info(f"Reduced ALL rules to {len(all_rules)} rows")
        
        # --- Step 2: Merge ALL rules on exchange+segment ---
        self.ccp_combined = pd.merge(
            self.ccp_sec,
            all_rules,
            on=merge_keys,
            how="left",
            validate="m:1"
        )
        logger.info(f"After ALL-rules merge: {self.ccp_combined.shape}")
        
        # --- Step 3: Override with symbol-specific rules ---
        if has_mic_code and len(symbol_rules) > 0:
            self._apply_symbol_specific_rules(symbol_rules, merge_keys)
        
        # --- Step 4: Fallback for EXCEPTION_INCLUSION ---
        if has_segment:
            self._fallback_exception_inclusion(all_rules, merge_keys)
        
        # --- Log merge results ---
        self._log_merge_diagnostics(all_rules, merge_keys)
    
    def _apply_symbol_specific_rules(self, symbol_rules, merge_keys):
        """
        Apply symbol-specific Market Rules (mic_code != 'ALL').
        
        For each symbol-specific rule, find matching securities by
        symbol + exchange + segment and overwrite the base ALL-rule values.
        The mic_code field contains the symbol name for symbol-specific rules.
        
        Args:
            symbol_rules: DataFrame of Market Rules where mic_code is a symbol name
            merge_keys: List of merge key column names (['exchange', 'segment'] or ['exchange'])
        """
        logger.info(f"Applying {len(symbol_rules)} symbol-specific rules...")
        
        # Identify rule-value columns (everything that came from Market Rules, 
        # excluding merge keys and mic_code itself)
        sec_non_key_cols = set(self.ccp_sec.columns) - set(merge_keys)
        
        overridden_count = 0
        for _, rule_row in symbol_rules.iterrows():
            target_symbol = str(rule_row['mic_code']).strip().upper()
            
            # Build match mask: symbol matches mic_code AND exchange+segment match
            symbol_col_upper = self.ccp_combined[self.ccp_symbol_col].astype(str).str.strip().str.upper()
            match_mask = symbol_col_upper == target_symbol
            
            for key in merge_keys:
                match_mask = match_mask & (self.ccp_combined[key] == rule_row[key])
            
            matched_count = match_mask.sum()
            if matched_count == 0:
                logger.warning(
                    f"Symbol-specific rule for '{target_symbol}' "
                    f"({', '.join(f'{k}={rule_row[k]}' for k in merge_keys)}) "
                    f"matched 0 securities"
                )
                continue
            
            # Override rule columns for matched securities
            for rule_col in symbol_rules.columns:
                if rule_col in merge_keys or rule_col == 'mic_code':
                    continue
                # Determine target column name (may have _y suffix if shared)
                if rule_col in sec_non_key_cols:
                    target_col = f"{rule_col}_y"
                else:
                    target_col = rule_col
                if target_col in self.ccp_combined.columns:
                    self.ccp_combined.loc[match_mask, target_col] = rule_row[rule_col]
            
            # Also override mic_code column in combined df so it shows the
            # symbol-specific value instead of "ALL"
            mic_code_col = 'mic_code'
            if mic_code_col not in self.ccp_combined.columns:
                # mic_code may have been suffixed during merge
                for suffix in ['_x', '_y']:
                    if f'mic_code{suffix}' in self.ccp_combined.columns:
                        mic_code_col = f'mic_code{suffix}'
                        break
            # Update the rules-side mic_code (or the only one)
            if 'mic_code_y' in self.ccp_combined.columns:
                self.ccp_combined.loc[match_mask, 'mic_code_y'] = target_symbol
            elif 'mic_code' in self.ccp_combined.columns:
                self.ccp_combined.loc[match_mask, 'mic_code'] = target_symbol
            
            overridden_count += matched_count
            logger.info(
                f"  Symbol rule '{target_symbol}' "
                f"({', '.join(f'{k}={rule_row[k]}' for k in merge_keys)}): "
                f"overrode {matched_count} securities"
            )
        
        logger.info(f"Symbol-specific rules: {overridden_count} total securities overridden")

    def _log_merge_diagnostics(self, rules_df, merge_keys):
        """Log merge result diagnostics and unmatched rows."""
        sec_non_key_cols = set(self.ccp_sec.columns) - set(merge_keys)
        rule_only_cols = [
            c for c in rules_df.columns
            if c not in merge_keys and c not in sec_non_key_cols
        ]
        
        if rule_only_cols:
            check_col = rule_only_cols[0]
            unmatched_mask = self.ccp_combined[check_col].isna()
            unmatched_count = unmatched_mask.sum()
        else:
            shared_rule_cols = [
                c for c in rules_df.columns
                if c not in merge_keys and c in sec_non_key_cols
            ]
            if shared_rule_cols:
                check_col = f"{shared_rule_cols[0]}_y"
                unmatched_mask = self.ccp_combined[check_col].isna()
                unmatched_count = unmatched_mask.sum()
            else:
                unmatched_count = 0
                unmatched_mask = pd.Series([False] * len(self.ccp_combined))
        
        logger.info(f"CCP combined shape: {self.ccp_combined.shape}")
        logger.info(f"CCP combined columns: {len(self.ccp_combined.columns)}")
        
        if unmatched_count > 0:
            logger.warning(f"{unmatched_count} securities did not match any Market Rules")
            unmatched_keys = self.ccp_combined[unmatched_mask][merge_keys].drop_duplicates()
            for _, row in unmatched_keys.iterrows():
                logger.warning(f"  No rules found for: {dict(row)}")
            
            rules_keys = rules_df[merge_keys].drop_duplicates()
            logger.info(f"Available Market Rules keys ({len(rules_keys)} combinations):")
            for _, row in rules_keys.iterrows():
                logger.info(f"  Rules: {dict(row)}")

    def _fallback_exception_inclusion(self, ccp_rules_unique, merge_keys):
        """
        For EXCEPTION_INCLUSION securities that got no Market Rules after the
        initial merge (because no EXCEPTION_INCLUSION rule exists for that
        exchange), reclassify them to their actual segment (US_EQUITY, US_ETP,
        EUROPEAN_EQUITY, etc.) and fill in the rules from the matching
        exchange+segment rule row.
        """
        # Identify rule-only columns (columns that came from Market Rules, not Security)
        sec_non_key_cols = set(self.ccp_sec.columns) - set(merge_keys)
        rule_only_cols = [
            c for c in ccp_rules_unique.columns
            if c not in merge_keys and c not in sec_non_key_cols
        ]
        # If all rule cols overlap with security cols, use suffixed names
        if not rule_only_cols:
            shared = [c for c in ccp_rules_unique.columns if c not in merge_keys and c in sec_non_key_cols]
            rule_only_cols = [f"{c}_y" for c in shared]
        
        if not rule_only_cols:
            return
        
        check_col = rule_only_cols[0]
        
        # Find EXCEPTION_INCLUSION rows that have no rules
        exc_mask = (
            (self.ccp_combined['segment'] == 'EXCEPTION_INCLUSION') &
            (self.ccp_combined[check_col].isna())
        )
        exc_count = exc_mask.sum()
        
        if exc_count == 0:
            return
        
        logger.info(f"Fallback: {exc_count} EXCEPTION_INCLUSION securities have no rules, reclassifying...")
        
        # Detect tcl1 column
        tcl1_col = None
        for col in ['tcl1', 'tcl_1', 'traded_products']:
            if col in self.ccp_combined.columns:
                tcl1_col = col
                break
        
        # For each unmatched EXCEPTION_INCLUSION row, determine actual segment
        reclassified = 0
        for idx in self.ccp_combined[exc_mask].index:
            exchange = self.ccp_combined.at[idx, 'exchange']
            tcl1_value = self.ccp_combined.at[idx, tcl1_col] if tcl1_col else None
            
            actual_segment = classify_security(exchange, tcl1_value)
            if actual_segment:
                actual_segment_key = actual_segment.replace(' ', '_')
                
                # Find the matching rule row
                rule_match = ccp_rules_unique[
                    (ccp_rules_unique['exchange'] == exchange) &
                    (ccp_rules_unique['segment'] == actual_segment_key)
                ]
                
                if not rule_match.empty:
                    rule_row = rule_match.iloc[0]
                    # Fill in rule columns from the matched rule
                    for rule_col in ccp_rules_unique.columns:
                        if rule_col in merge_keys:
                            continue
                        # Determine the target column name in the combined df
                        if rule_col in sec_non_key_cols:
                            target_col = f"{rule_col}_y"
                        else:
                            target_col = rule_col
                        if target_col in self.ccp_combined.columns:
                            self.ccp_combined.at[idx, target_col] = rule_row[rule_col]
                    reclassified += 1
        
        logger.info(
            f"Fallback complete: {reclassified}/{exc_count} EXCEPTION_INCLUSION "
            f"securities got rules from their actual segment"
        )

    def get_combined(self):
        """
        Get the combined CCP dataframe
        
        Returns:
            pd.DataFrame: Combined CCP grid (Security + Market Rules)
        """
        if self.ccp_combined is None:
            raise ValueError("CCP data has not been combined. Call combine() first.")
        return self.ccp_combined
    
    def get_symbol_column(self):
        """
        Get the detected symbol column name
        
        Returns:
            str: Symbol column name
        """
        if self.ccp_symbol_col is None:
            raise ValueError("Symbol column has not been detected. Call combine() first.")
        return self.ccp_symbol_col
