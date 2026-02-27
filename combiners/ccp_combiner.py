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
        
    def combine(self):
        """
        Combine CCP datasets
        
        Returns:
            CCPCombiner: self for method chaining
        """
        self._detect_symbol_column()
        self._normalize_segment_values()
        self._merge_datasets()
        return self
    
    def _normalize_segment_values(self):
        """
        Normalize merge key values (exchange and segment) in both CCP Security 
        Whitelist and Market Rules to uppercase, trimmed, with underscores for 
        consistent matching.
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
        Merge CCP Security Whitelist with CCP Market Rules
        
        Uses 'exchange' and 'segment' as merge keys with many-to-one relationship
        (many securities per exchange+segment, one rule set per exchange+segment)
        
        This ensures each security gets the correct Market Rules for its segment.
        For example, an AMEX US_ETP security gets US_ETP rules, not US_EQUITY rules.
        
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
        
        # Check for duplicate merge key combinations in Market Rules
        if all(k in self.ccp_rules.columns for k in merge_keys):
            duplicates = self.ccp_rules.duplicated(subset=merge_keys).sum()
            if duplicates > 0:
                logger.warning(f"Found {duplicates} duplicate {merge_keys} entries in CCP Market Rules")
                logger.info("Keeping first occurrence of each combination")
                ccp_rules_unique = self.ccp_rules.drop_duplicates(subset=merge_keys, keep='first')
                logger.info(f"Reduced Market Rules from {len(self.ccp_rules)} to {len(ccp_rules_unique)} rows")
            else:
                ccp_rules_unique = self.ccp_rules
        else:
            ccp_rules_unique = self.ccp_rules
        
        self.ccp_combined = pd.merge(
            self.ccp_sec,
            ccp_rules_unique,
            on=merge_keys,
            how="left",
            validate="m:1"
        )
        
        # --- Fallback: EXCEPTION_INCLUSION rows with no rules ---
        # Some exchanges (e.g. NSDQ) may not have EXCEPTION_INCLUSION rules in
        # CCP_Market_Rules.  For those, reclassify to actual segment via
        # classify_security() and re-merge with the correct segment rules.
        if has_segment:
            self._fallback_exception_inclusion(ccp_rules_unique, merge_keys)
        
        # Log merge results and diagnose unmatched rows
        # Identify a rule-only column (not a merge key and not shared with security df)
        # After merge, shared columns get _x/_y suffixes, so look for columns
        # that actually exist in the combined result
        sec_non_key_cols = set(self.ccp_sec.columns) - set(merge_keys)
        rule_only_cols = [
            c for c in ccp_rules_unique.columns 
            if c not in merge_keys and c not in sec_non_key_cols
        ]
        
        if rule_only_cols:
            check_col = rule_only_cols[0]
            unmatched_mask = self.ccp_combined[check_col].isna()
            unmatched_count = unmatched_mask.sum()
        else:
            # All rule columns overlap with security columns; use suffixed name
            shared_rule_cols = [
                c for c in ccp_rules_unique.columns
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
            # Log the unmatched exchange+segment combinations
            unmatched_keys = self.ccp_combined[unmatched_mask][merge_keys].drop_duplicates()
            for _, row in unmatched_keys.iterrows():
                logger.warning(f"  No rules found for: {dict(row)}")
            
            # Log available rules keys for comparison
            rules_keys = ccp_rules_unique[merge_keys].drop_duplicates()
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
