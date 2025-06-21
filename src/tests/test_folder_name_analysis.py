#!/usr/bin/env python3
"""
Test script to analyze all Dropbox folder names and show expected accounts for each folder.
This helps verify that the account parsing logic is working correctly for all cases.
"""

import sys
import os
import pytest
from typing import Dict, List, Any

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sync.analyzers.account_analyzer import AccountAnalyzer

class TestFolderNameAnalysis:
    """Test class for analyzing Dropbox folder names and expected accounts."""
    
    @pytest.fixture
    def analyzer(self):
        """Create an AccountAnalyzer instance for testing."""
        return AccountAnalyzer()
    
    @pytest.fixture
    def folder_names(self):
        """Load folder names from the dropbox_folder_names.txt file."""
        file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'dropbox_folder_names.txt')
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            # Clean up lines and remove empty ones
            folder_names = [line.strip() for line in lines if line.strip()]
            return folder_names
        except FileNotFoundError:
            pytest.skip(f"Could not find {file_path}")
        except Exception as e:
            pytest.skip(f"Error reading {file_path}: {e}")
    
    def analyze_folder_name(self, analyzer: AccountAnalyzer, folder_name: str) -> Dict[str, Any]:
        """Analyze a single folder name and return the analysis results."""
        try:
            # Analyze the folder name
            folder_analysis = analyzer._analyze_dropbox_folder_name(folder_name)
            
            # Generate expected Salesforce mapping
            expected_mapping = analyzer._generate_expected_salesforce_mapping(folder_analysis, None)
            
            # Generate name variations for testing
            name_variations = analyzer._generate_name_variations(folder_name)
            
            return {
                'folder_name': folder_name,
                'folder_analysis': folder_analysis,
                'expected_mapping': expected_mapping,
                'name_variations': name_variations
            }
        except Exception as e:
            return {
                'folder_name': folder_name,
                'error': str(e),
                'folder_analysis': None,
                'expected_mapping': None,
                'name_variations': []
            }
    
    def categorize_results(self, results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize results by type for better analysis."""
        categories = {
            'simple_names': [],      # Simple "Last, First" or "First Last"
            'nicknames': [],         # Names with parentheses (nicknames)
            'joint_accounts': [],    # Names with "&" or "and"
            'children_info': [],     # Names with "son", "daughter", etc.
            'complex_names': [],     # Other complex patterns
            'errors': []             # Names that caused errors
        }
        
        for result in results:
            if 'error' in result:
                categories['errors'].append(result)
                continue
                
            folder_analysis = result['folder_analysis']
            folder_name = result['folder_name']
            
            # Check for different patterns
            if folder_analysis['is_joint_account']:
                categories['joint_accounts'].append(result)
            elif '(' in folder_name and ')' in folder_name:
                categories['nicknames'].append(result)
            elif any(word in folder_name.lower() for word in ['son', 'daughter', 'children']):
                categories['children_info'].append(result)
            elif ',' in folder_name or len(folder_name.split()) == 2:
                categories['simple_names'].append(result)
            else:
                categories['complex_names'].append(result)
        
        return categories
    
    def test_all_folder_names_analysis(self, analyzer, folder_names):
        """Test that all folder names can be analyzed without errors."""
        results = []
        
        for folder_name in folder_names:
            result = self.analyze_folder_name(analyzer, folder_name)
            results.append(result)
        
        # Check that there are no errors
        errors = [r for r in results if 'error' in r]
        assert len(errors) == 0, f"Found {len(errors)} errors in folder name analysis"
        
        # Check that we have results
        assert len(results) > 0, "No results generated"
        
        # Categorize results
        categories = self.categorize_results(results)
        
        # Basic assertions about the results
        assert len(categories['simple_names']) > 0, "No simple names found"
        assert len(categories['nicknames']) > 0, "No names with nicknames found"
        assert len(categories['joint_accounts']) > 0, "No joint accounts found"
        assert len(categories['children_info']) > 0, "No names with children info found"
        
        print(f"\n📊 Analysis Summary:")
        print(f"   Total folder names: {len(results)}")
        print(f"   Simple names: {len(categories['simple_names'])}")
        print(f"   Names with nicknames: {len(categories['nicknames'])}")
        print(f"   Joint accounts: {len(categories['joint_accounts'])}")
        print(f"   Names with children info: {len(categories['children_info'])}")
        print(f"   Complex names: {len(categories['complex_names'])}")
        print(f"   Errors: {len(categories['errors'])}")
    
    def test_specific_folder_names(self, analyzer):
        """Test specific folder names that are known to be problematic."""
        test_cases = [
            "Bisono, Fernando (Medicaid Mike)",
            "Rubino, Salvatore & Maria",
            "McNabb, Frances daughter Pam Murphy",
            "Kazakian, George (Mike)",
            "Bauer Glenn and Brenda"
        ]
        
        for folder_name in test_cases:
            result = self.analyze_folder_name(analyzer, folder_name)
            
            # Check no errors
            assert 'error' not in result, f"Error analyzing '{folder_name}': {result.get('error')}"
            
            # Check that we have analysis results
            assert result['folder_analysis'] is not None, f"No folder analysis for '{folder_name}'"
            assert result['expected_mapping'] is not None, f"No expected mapping for '{folder_name}'"
            assert len(result['name_variations']) > 0, f"No name variations for '{folder_name}'"
            
            print(f"\n✅ {folder_name}:")
            print(f"   Parsed names: {result['folder_analysis']['parsed_names']}")
            print(f"   Expected accounts: {len(result['expected_mapping']['accounts'])}")
            print(f"   Name variations: {len(result['name_variations'])}")
    
    def test_no_malformed_names(self, analyzer, folder_names):
        """Test that no malformed names are generated (like 'bisono, fern')."""
        problematic_patterns = [
            'bisono, fern',
            'o (medicaid mike)',
            'fern, bisono',
            'medicaid mike, o'
        ]
        
        for folder_name in folder_names:
            result = self.analyze_folder_name(analyzer, folder_name)
            
            if 'error' in result:
                continue
            
            # Check name variations don't contain problematic patterns
            for variation in result['name_variations']:
                for pattern in problematic_patterns:
                    assert pattern not in variation.lower(), \
                        f"Found malformed name '{pattern}' in variations for '{folder_name}': {result['name_variations']}"
            
            # Check expected accounts don't contain problematic patterns
            for account in result['expected_mapping'].get('accounts', []):
                account_name = account['name']
                for pattern in problematic_patterns:
                    assert pattern not in account_name.lower(), \
                        f"Found malformed name '{pattern}' in expected account for '{folder_name}': {account_name}"
    
    def test_nickname_handling(self, analyzer):
        """Test that nicknames in parentheses are handled correctly."""
        test_cases = [
            ("Bisono, Fernando (Medicaid Mike)", "Fernando Bisono"),
            ("Kazakian, George (Mike)", "George Kazakian"),
            ("Frost, Theresia (Mike)", "Theresia Frost")
        ]
        
        for folder_name, expected_clean_name in test_cases:
            result = self.analyze_folder_name(analyzer, folder_name)
            
            assert 'error' not in result, f"Error analyzing '{folder_name}': {result.get('error')}"
            
            # Check that the first parsed name is the clean version (without nickname)
            parsed_names = result['folder_analysis']['parsed_names']
            assert len(parsed_names) > 0, f"No parsed names for '{folder_name}'"
            
            first_parsed_name = parsed_names[0]
            assert expected_clean_name in first_parsed_name, \
                f"Expected '{expected_clean_name}' in first parsed name '{first_parsed_name}' for '{folder_name}'"
            
            print(f"✅ {folder_name} → {first_parsed_name}")
    
    def test_joint_account_detection(self, analyzer):
        """Test that joint accounts are correctly detected."""
        joint_accounts = [
            "Rubino, Salvatore & Maria",
            "Bauer Glenn and Brenda",
            "Martinez, Hector and Margarita"
        ]
        
        for folder_name in joint_accounts:
            result = self.analyze_folder_name(analyzer, folder_name)
            
            assert 'error' not in result, f"Error analyzing '{folder_name}': {result.get('error')}"
            
            # Check that it's detected as a joint account
            assert result['folder_analysis']['is_joint_account'], \
                f"'{folder_name}' should be detected as joint account"
            
            # Check that we have two expected accounts
            expected_accounts = result['expected_mapping']['accounts']
            assert len(expected_accounts) == 2, \
                f"Expected 2 accounts for joint account '{folder_name}', got {len(expected_accounts)}"
            
            print(f"✅ {folder_name}: Joint account with {len(expected_accounts)} expected accounts")
    
    def test_children_info_extraction(self, analyzer):
        """Test that children information is correctly extracted."""
        children_cases = [
            ("McNabb, Frances daughter Pam Murphy", ["Pam Murphy"]),
            ("Albert, Ethel son Howard", ["Howard"]),
            ("Mendez, Onelio daughter Iliana Hambleton", ["Iliana Hambleton"])
        ]
        
        for folder_name, expected_children in children_cases:
            result = self.analyze_folder_name(analyzer, folder_name)
            
            assert 'error' not in result, f"Error analyzing '{folder_name}': {result.get('error')}"
            
            # Check that children info is extracted
            children_info = result['folder_analysis']['children_info']
            for expected_child in expected_children:
                assert any(expected_child in child for child in children_info), \
                    f"Expected child '{expected_child}' not found in children info for '{folder_name}': {children_info}"
            
            print(f"✅ {folder_name}: Children info extracted: {children_info}")


def run_comprehensive_analysis():
    """Run a comprehensive analysis and save results to file."""
    analyzer = AccountAnalyzer()
    
    # Load folder names
    file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'dropbox_folder_names.txt')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        folder_names = [line.strip() for line in lines if line.strip()]
    except FileNotFoundError:
        print(f"Error: Could not find {file_path}")
        return
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return
    
    print(f"📁 Loaded {len(folder_names)} folder names from dropbox_folder_names.txt")
    
    # Analyze each folder name
    results = []
    for i, folder_name in enumerate(folder_names, 1):
        print(f"   Processing {i}/{len(folder_names)}: {folder_name}")
        
        try:
            folder_analysis = analyzer._analyze_dropbox_folder_name(folder_name)
            expected_mapping = analyzer._generate_expected_salesforce_mapping(folder_analysis, None)
            name_variations = analyzer._generate_name_variations(folder_name)
            
            results.append({
                'folder_name': folder_name,
                'folder_analysis': folder_analysis,
                'expected_mapping': expected_mapping,
                'name_variations': name_variations
            })
        except Exception as e:
            results.append({
                'folder_name': folder_name,
                'error': str(e),
                'folder_analysis': None,
                'expected_mapping': None,
                'name_variations': []
            })
    
    # Categorize results
    test_instance = TestFolderNameAnalysis()
    categories = test_instance.categorize_results(results)
    
    # Print summary
    print("\n" + "="*80)
    print("📊 ANALYSIS SUMMARY")
    print("="*80)
    
    print(f"📁 Total Folder Names Analyzed: {len(folder_names)}")
    print(f"✅ Successful Analyses: {len(folder_names) - len(categories['errors'])}")
    print(f"❌ Errors: {len(categories['errors'])}")
    print()
    
    print("📋 Breakdown by Category:")
    print(f"   • Simple Names: {len(categories['simple_names'])}")
    print(f"   • Names with Nicknames: {len(categories['nicknames'])}")
    print(f"   • Joint Accounts: {len(categories['joint_accounts'])}")
    print(f"   • Names with Children Info: {len(categories['children_info'])}")
    print(f"   • Complex Names: {len(categories['complex_names'])}")
    print(f"   • Errors: {len(categories['errors'])}")
    
    # Save results to file
    output_file = os.path.join(os.path.dirname(__file__), '..', '..', 'folder_analysis_results.txt')
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("Dropbox Folder Name Analysis Results\n")
            f.write("="*50 + "\n\n")
            
            f.write("SUMMARY\n")
            f.write("-"*20 + "\n")
            f.write(f"Total Folder Names Analyzed: {len(folder_names)}\n")
            f.write(f"Successful Analyses: {len(folder_names) - len(categories['errors'])}\n")
            f.write(f"Errors: {len(categories['errors'])}\n\n")
            
            for category_name, category_results in categories.items():
                f.write(f"{category_name}: {len(category_results)}\n")
            
            f.write("\n" + "="*50 + "\n")
            f.write("DETAILED RESULTS\n")
            f.write("="*50 + "\n\n")
            
            for result in results:
                if 'error' in result:
                    f.write(f"❌ {result['folder_name']}: ERROR - {result['error']}\n\n")
                else:
                    f.write(f"📁 {result['folder_name']}\n")
                    f.write(f"   📋 Analysis:\n")
                    f.write(f"     • Joint Account: {'✅ Yes' if result['folder_analysis']['is_joint_account'] else '❌ No'}\n")
                    f.write(f"     • Parsed Names: {result['folder_analysis']['parsed_names']}\n")
                    
                    if result['folder_analysis']['primary_account_holder']:
                        f.write(f"     • Primary: {result['folder_analysis']['primary_account_holder']}\n")
                    if result['folder_analysis']['joint_account_holder']:
                        f.write(f"     • Joint: {result['folder_analysis']['joint_account_holder']}\n")
                    if result['folder_analysis']['children_info']:
                        f.write(f"     • Children: {result['folder_analysis']['children_info']}\n")
                    
                    f.write(f"   🏠 Expected Household: {result['expected_mapping']['household']['name'] or 'None'}\n")
                    
                    accounts = result['expected_mapping'].get('accounts', [])
                    if accounts:
                        f.write(f"   👥 Expected Accounts ({len(accounts)}):\n")
                        for i, account in enumerate(accounts, 1):
                            f.write(f"     {i}. {account['name']} ({account['type']}, {account['role']})\n")
                    else:
                        f.write(f"   👥 Expected Accounts: None\n")
                    
                    f.write(f"   🔄 Name Variations ({len(result['name_variations'])}):\n")
                    for i, variation in enumerate(result['name_variations'], 1):
                        f.write(f"     {i}. {variation}\n")
                    
                    f.write("\n")
        
        print(f"\n💾 Detailed results saved to: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Error saving results to file: {e}")
    
    print("\n✅ Analysis complete!")


if __name__ == "__main__":
    # Run comprehensive analysis when script is run directly
    run_comprehensive_analysis() 