"""
Task-based system instructions loader for contract analysis
"""
import os
from typing import Optional
from logger_config import get_logger

logger = get_logger(__name__)

INSTRUCTIONS_DIR = os.path.join(os.path.dirname(__file__), "system_instructions")

# Mapping of contract types to instruction files
CONTRACT_TYPE_TEMPLATES = {
    "vendor_agreement": "vendor_agreement.txt",
    "nda": "nda.txt",
    "employment_contract": "employment_contract.txt",
    "service_agreement": "service_agreement.txt",
    "saas_agreement": "saas_agreement.txt",
    "license_agreement": "license_agreement.txt",
    "default": "contract_analysis.txt"  # Fallback
}


def get_system_instructions_for_contract(contract_type: Optional[str] = None) -> str:
    """
    Load system instructions based on contract type
    
    Args:
        contract_type: Type of contract (e.g., "vendor_agreement", "nda")
    
    Returns:
        System instructions text
    """
    # Default to general contract analysis if no type specified
    if not contract_type or contract_type.lower() == "unknown":
        template_file = CONTRACT_TYPE_TEMPLATES["default"]
    else:
        # Normalize contract type (lowercase, replace spaces with underscores)
        normalized_type = contract_type.lower().replace(" ", "_").replace("-", "_")
        template_file = CONTRACT_TYPE_TEMPLATES.get(normalized_type, CONTRACT_TYPE_TEMPLATES["default"])
    
    template_path = os.path.join(INSTRUCTIONS_DIR, template_file)
    
    try:
        with open(template_path, 'r') as f:
            instructions = f.read()
            logger.info(f"Loaded system instructions from: {template_file}")
            return instructions
    except FileNotFoundError:
        logger.warning(f"Template not found: {template_file}, using default")
        # Fallback to default
        default_path = os.path.join(INSTRUCTIONS_DIR, CONTRACT_TYPE_TEMPLATES["default"])
        with open(default_path, 'r') as f:
            return f.read()


def list_available_templates() -> list[dict]:
    """
    List all available contract analysis templates
    
    Returns:
        List of template info dicts
    """
    templates = []
    for contract_type, filename in CONTRACT_TYPE_TEMPLATES.items():
        template_path = os.path.join(INSTRUCTIONS_DIR, filename)
        exists = os.path.exists(template_path)
        
        templates.append({
            "contract_type": contract_type,
            "filename": filename,
            "exists": exists,
            "path": template_path if exists else None
        })
    
    return templates
