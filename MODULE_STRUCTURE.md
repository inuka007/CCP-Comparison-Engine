# Module Structure

This document describes the modular architecture of the CCP-AT Comparison Engine.

## Directory Structure

```
CCP AT Comparison Engine/
├── mappings/                   # Configuration mappings
│   ├── __init__.py
│   ├── column_mappings.py     # CCP ↔ AT column mappings
│   └── segment_mapping.py     # Exchange ↔ Segment/Region mappings
│
├── combiners/                  # Data combination logic
│   ├── __init__.py
│   └── ccp_combiner.py        # Combines CCP Security + Market Rules
│
├── analyzers/                  # Analysis engines
│   ├── __init__.py
│   └── requirements_analyzer.py  # Requirements 1, 2, 3 analysis
│
├── compare_engine.py          # Main comparison orchestrator
├── app.py                     # Flask web application
├── wsgi.py                    # WSGI entry point
│
├── static/                    # Web assets
│   ├── script.js
│   └── style.css
│
├── templates/                 # HTML templates
│   └── index.html
│
├── tests/                     # Unit tests
│   ├── test_ccp_combiner.py
│   └── test_requirements_analyzer.py
│
├── temp_uploads/              # Temporary file uploads
└── temp_results/              # Temporary results cache
```

## Module Responsibilities

### 📁 mappings/
**Purpose**: Centralized configuration for all mappings

- **column_mappings.py**
  - Maps CCP columns to AT columns
  - Defines excluded columns
  - Helper functions for column comparison logic

- **segment_mapping.py**
  - Maps exchanges to regions (US, EUROPE, ASIA)
  - Classifies securities as Equity or ETP
  - Generates segment names (e.g., "US EQUITY", "EUROPEAN ETP")

### 📁 combiners/
**Purpose**: Data combination and preprocessing logic

- **ccp_combiner.py**
  - `CCPCombiner` class
  - Merges CCP Security Whitelist with CCP Market Rules
  - Handles exchange-based many-to-one relationship
  - Auto-detects symbol columns

### 📁 analyzers/
**Purpose**: Business logic for requirements analysis

- **requirements_analyzer.py**
  - `RequirementsAnalyzer` class
  - **Requirement 1**: Securities in CCP but not in AT (with segment summary)
  - **Requirement 2**: Securities in AT but not in CCP
  - **Requirement 3**: Configuration mismatches (with pivot summary)
  - Generates summary reports and pivot tables

### 🔧 Core Engine

- **compare_engine.py**
  - `ComparisonEngine` class
  - Orchestrates the entire comparison workflow
  - Delegates to combiners and analyzers
  - Generates statistics and results

### 🌐 Web Application

- **app.py**
  - Flask web server
  - File upload and validation
  - Result caching and downloads
  - Multi-sheet Excel generation

## Import Patterns

### From Root Modules
```python
from compare_engine import ComparisonEngine, ValidationError
```

### From Mappings
```python
from mappings.column_mappings import get_mapped_columns, COLUMN_MAPPINGS
from mappings.segment_mapping import classify_security, is_etp
```

### From Combiners
```python
from combiners.ccp_combiner import CCPCombiner
```

### From Analyzers
```python
from analyzers.requirements_analyzer import RequirementsAnalyzer
```

## Benefits of Modular Structure

1. **Separation of Concerns**: Each module has a single, well-defined responsibility
2. **Maintainability**: Easy to locate and update specific functionality
3. **Testability**: Modules can be tested independently
4. **Scalability**: New combiners, analyzers, or mappings can be added easily
5. **Code Reusability**: Modules can be imported and reused across different contexts

## Adding New Modules

### New Mapping
Create a new file in `mappings/` and update `mappings/__init__.py`:
```python
# mappings/custom_mapping.py
def get_custom_mapping():
    return {...}

# mappings/__init__.py
from .custom_mapping import get_custom_mapping
__all__ = [..., 'get_custom_mapping']
```

### New Combiner
Create a new file in `combiners/` and update `combiners/__init__.py`:
```python
# combiners/at_combiner.py
class ATCombiner:
    ...

# combiners/__init__.py
from .at_combiner import ATCombiner
__all__ = [..., 'ATCombiner']
```

### New Analyzer
Create a new file in `analyzers/` and update `analyzers/__init__.py`:
```python
# analyzers/rules_analyzer.py
class RulesAnalyzer:
    ...

# analyzers/__init__.py
from .rules_analyzer import RulesAnalyzer
__all__ = [..., 'RulesAnalyzer']
```

## Migration Notes

### Old Import Paths → New Import Paths

| Old | New |
|-----|-----|
| `from column_mappings import ...` | `from mappings.column_mappings import ...` |
| `from segment_mapping import ...` | `from mappings.segment_mapping import ...` |
| `from ccp_combiner import ...` | `from combiners.ccp_combiner import ...` |
| `from requirements_analyzer import ...` | `from analyzers.requirements_analyzer import ...` |

All imports have been updated in:
- ✅ `compare_engine.py`
- ✅ `analyzers/requirements_analyzer.py`

## Testing

Run tests to verify the modular structure:
```bash
python -m pytest tests/
```

Or run individual test files:
```bash
python -m pytest tests/test_ccp_combiner.py
python -m pytest tests/test_requirements_analyzer.py
```
