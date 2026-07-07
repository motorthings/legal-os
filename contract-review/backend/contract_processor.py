"""
Contract Processing Module
Handles contract analysis, risk scoring, and human-in-the-loop flagging
"""
import asyncio
import json
import os
import time
from typing import Dict, Any, Optional
from datetime import datetime

from anthropic import AsyncAnthropic
from database import get_supabase
from logger_config import get_logger
from pypdf import PdfReader
import docx
from instruction_versioning import (
    get_instruction_version,
    get_legal_standards_version
)
from processing_logger import log_processing_step

logger = get_logger(__name__)


# Performance timing helper
class PerformanceTimer:
    """Track performance metrics for contract processing stages"""
    def __init__(self, document_id: str):
        self.document_id = document_id
        self.timings = {}
        self.start_time = time.time()

    def start_stage(self, stage_name: str):
        """Start timing a processing stage"""
        self.timings[stage_name] = {'start': time.time()}

    def end_stage(self, stage_name: str, metadata: Dict = None):
        """End timing a processing stage and log results"""
        if stage_name not in self.timings:
            logger.warning(f"Stage {stage_name} was never started")
            return

        end_time = time.time()
        duration = end_time - self.timings[stage_name]['start']
        self.timings[stage_name]['end'] = end_time
        self.timings[stage_name]['duration'] = duration

        # Add metadata if provided
        if metadata:
            self.timings[stage_name]['metadata'] = metadata

        # Log the timing
        logger.info(
            f"⏱️ PERFORMANCE [{self.document_id}] {stage_name}: {duration:.2f}s" +
            (f" | {metadata}" if metadata else "")
        )

    def get_total_time(self) -> float:
        """Get total processing time"""
        return time.time() - self.start_time

    def get_summary(self) -> Dict[str, Any]:
        """Get complete performance summary"""
        total = self.get_total_time()
        return {
            'document_id': self.document_id,
            'total_time': round(total, 2),
            'stages': {
                name: {
                    'duration': round(timing['duration'], 2),
                    'percentage': round((timing['duration'] / total) * 100, 1),
                    'metadata': timing.get('metadata', {})
                }
                for name, timing in self.timings.items()
                if 'duration' in timing
            }
        }

# Lazy-load clients to avoid initialization errors at import time
_supabase = None
_anthropic_client = None

def get_supabase_client():
    """Get or initialize Supabase client"""
    global _supabase
    if _supabase is None:
        _supabase = get_supabase()
    return _supabase

def get_anthropic_client():
    """Get or initialize Async Anthropic client with timeout"""
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = AsyncAnthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
            timeout=600.0,  # 10 minute timeout for API calls (handles very large contracts)
            max_retries=1   # Retry failed requests once
        )
    return _anthropic_client

# System instructions directory
SYSTEM_INSTRUCTIONS_DIR = os.path.join(
    os.path.dirname(__file__),
    "system_instructions"
)

# Model settings for Claude API calls
# Configurable via environment variables for flexibility across different use cases
ROUTER_MODEL = os.environ.get("ROUTER_MODEL", "claude-sonnet-4-5-20250929")  # Default: Sonnet 4.5 for accurate classification
ANALYSIS_MODEL = os.environ.get("ANALYSIS_MODEL", "claude-sonnet-4-5-20250929")  # Default: Sonnet 4.5 for detailed analysis

# Temperature settings for Claude API calls
# Lower values (0.0-0.3) = more deterministic, consistent
# Higher values (0.7-1.0) = more creative, varied
ROUTER_TEMPERATURE = float(os.environ.get("ROUTER_TEMPERATURE", "0.1"))  # Very low for consistent classification
ANALYSIS_TEMPERATURE = float(os.environ.get("ANALYSIS_TEMPERATURE", "0.3"))  # Low-medium for detailed analysis


def load_system_instructions(instruction_type: str, client_id: Optional[str] = None) -> tuple[str, list]:
    """
    Load system instructions from database (or XML file fallback) and inject legal standards

    Args:
        instruction_type: Type of instructions to load
            - 'router': Router classification instructions (loaded from file only)
            - 'vendor': Vendor contract analysis instructions
            - 'customer': Customer contract analysis instructions
            - 'employment': Employment contract analysis instructions
            - 'dpa': DPA contract analysis instructions
            - 'general': General contract analysis instructions
            - 'legacy': Legacy contract_analysis.txt (fallback)
        client_id: Optional client ID for loading client-specific legal standards

    Returns:
        Tuple of (instructions string with legal standards injected, list of standards used)
    """
    instructions = None

    # Load router from separate router_instructions table
    if instruction_type == 'router':
        try:
            supabase = get_supabase_client()
            result = supabase.table('router_instructions')\
                .select('instructions')\
                .eq('is_active', True)\
                .single()\
                .execute()

            if result.data and result.data.get('instructions'):
                instructions = result.data['instructions']
                logger.info(f"✅ Loaded router instructions from database")
        except Exception as e:
            logger.warning(f"Failed to load router instructions from database: {e}, falling back to file")

    # Try to load from database first for contract-type specific instructions
    elif instruction_type in ['vendor', 'customer', 'employment', 'dpa', 'general', 'other']:
        try:
            supabase = get_supabase_client()
            result = supabase.table('contract_type_instructions')\
                .select('instructions')\
                .eq('contract_type', instruction_type)\
                .single()\
                .execute()

            if result.data and result.data.get('instructions'):
                instructions = result.data['instructions']
                logger.info(f"✅ Loaded {instruction_type} instructions from database")
        except Exception as e:
            logger.warning(f"Failed to load {instruction_type} instructions from database: {e}, falling back to file")

    # Fallback to file system if database load failed or for router instructions
    if instructions is None:
        instruction_files = {
            'router': 'ROUTER_SYSTEM_INSTRUCTIONS.xml',
            'vendor': 'VENDOR_CONTRACT_SYSTEM_INSTRUCTIONS.xml',
            'customer': 'CUSTOMER_CONTRACT_SYSTEM_INSTRUCTIONS.xml',
            'employment': 'EMPLOYMENT_CONTRACT_SYSTEM_INSTRUCTIONS.xml',
            'dpa': 'DPA_CONTRACT_SYSTEM_INSTRUCTIONS.xml',
            'general': 'GENERAL_CONTRACT_SYSTEM_INSTRUCTIONS.xml',
            'other': 'OTHER_CONTRACT_SYSTEM_INSTRUCTIONS.xml',
            'legacy': 'contract_analysis.txt'
        }

        filename = instruction_files.get(instruction_type)
        if not filename:
            raise ValueError(f"Unknown instruction type: {instruction_type}")

        file_path = os.path.join(SYSTEM_INSTRUCTIONS_DIR, filename)

        if not os.path.exists(file_path):
            logger.warning(f"System instructions not found: {file_path}, using legacy fallback")
            # Fallback to legacy instructions
            file_path = os.path.join(SYSTEM_INSTRUCTIONS_DIR, "contract_analysis.txt")

        with open(file_path, "r", encoding="utf-8") as f:
            instructions = f.read()
        logger.info(f"📄 Loaded {instruction_type} instructions from file: {filename}")

    # Load and inject legal standards if analyzing a specific contract type
    standards = []
    if instruction_type in ['vendor', 'customer', 'employment', 'dpa', 'general', 'other']:
        standards = load_legal_standards(client_id, instruction_type)
        standards_xml = format_legal_standards_xml(standards)

        # Inject standards before closing system_instructions tag
        if standards_xml and '</system_instructions>' in instructions:
            instructions = instructions.replace('</system_instructions>',
                                              f'{standards_xml}</system_instructions>')
            logger.info(f"Injected {len(standards)} legal standards into {instruction_type} instructions")

    return instructions, standards


from datetime import datetime, timedelta

# Cache for legal standards with TTL
_legal_standards_cache = {}
_cache_ttl = timedelta(hours=1)  # Refresh every hour

def load_legal_standards(client_id: Optional[str], contract_type: str) -> list[Dict]:
    """
    Load applicable legal standards for contract analysis (with 1-hour cache)

    Args:
        client_id: Optional client ID for client-specific standards
        contract_type: Contract type (vendor/customer/employment/dpa/general)

    Returns:
        List of legal standard dictionaries
    """
    # Generate cache key
    cache_key = f"{client_id or 'default'}:{contract_type}"

    # Check cache
    if cache_key in _legal_standards_cache:
        cached_data, cached_time = _legal_standards_cache[cache_key]
        if datetime.now() - cached_time < _cache_ttl:
            logger.debug(f"✅ Using cached legal standards for {cache_key} ({len(cached_data)} standards)")
            return cached_data
        else:
            logger.debug(f"⏰ Cache expired for {cache_key}, refreshing...")

    # Cache miss or expired - fetch from database
    try:
        supabase = get_supabase_client()

        # Load standards for this contract type + 'all' types
        query = supabase.table('legal_standards')\
            .select('*')\
            .eq('is_active', True)\
            .in_('contract_type', [contract_type, 'all'])

        # Include client-specific + defaults (NULL client_id)
        if client_id:
            query = query.or_(f'client_id.is.null,client_id.eq.{client_id}')
        else:
            query = query.is_('client_id', 'null')

        result = query.execute()
        standards = result.data or []

        # Store in cache
        _legal_standards_cache[cache_key] = (standards, datetime.now())
        logger.info(f"📋 Loaded and cached {len(standards)} legal standards for {contract_type}")
        return standards

    except Exception as e:
        logger.warning(f"Failed to load legal standards: {str(e)}")
        return []


def format_legal_standards_xml(standards: list[Dict]) -> str:
    """
    Format legal standards as XML for injection into system instructions

    Args:
        standards: List of legal standard dictionaries

    Returns:
        XML-formatted standards string
    """
    if not standards:
        return ""

    xml = "\n\n<legal_standards>\n"
    xml += "<!-- Compare extracted contract terms against these standards and generate flags -->\n"

    for std in standards:
        xml += f"""  <standard severity="{std['violation_severity']}">
    <category>{std['category']}</category>
    <term>{std['term_name']}</term>
    <description>{std['description']}</description>
    <acceptable_values>{json.dumps(std['acceptable_values'])}</acceptable_values>
    <recommendation>{std.get('recommendation', 'Review with legal team')}</recommendation>
  </standard>\n"""

    xml += "</legal_standards>\n"
    return xml


def extract_text_from_document(file_path: str, mime_type: str) -> tuple[str, int]:
    """
    Extract text content from various document formats

    Args:
        file_path: Path to the document file
        mime_type: MIME type of the document

    Returns:
        Tuple of (extracted text content, page count)
    """
    try:
        page_count = 0

        if mime_type == "application/pdf" or file_path.endswith('.pdf'):
            # Try PyPDF2 first
            reader = PdfReader(file_path)
            page_count = len(reader.pages)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n\n"

            # If PyPDF2 fails to extract sufficient text, try pdfplumber as fallback
            if len(text.strip()) < 100:
                logger.warning(f"PyPDF2 extracted insufficient text ({len(text.strip())} chars), trying pdfplumber fallback")
                try:
                    import pdfplumber
                    with pdfplumber.open(file_path) as pdf:
                        page_count = len(pdf.pages)
                        text = ""
                        for page in pdf.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n\n"
                    logger.info(f"pdfplumber extracted {len(text.strip())} characters from {page_count} pages")
                except Exception as plumber_error:
                    logger.error(f"pdfplumber extraction also failed: {str(plumber_error)}")
                    # Return PyPDF2 result even if insufficient

            return text, page_count

        elif mime_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"] or file_path.endswith('.docx'):
            doc = docx.Document(file_path)
            text = "\n\n".join([paragraph.text for paragraph in doc.paragraphs])
            # Estimate page count based on typical page length (500 words ~= 1 page)
            word_count = len(text.split())
            page_count = max(1, word_count // 500)
            return text, page_count

        elif mime_type.startswith("text/") or file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            # Estimate page count based on typical page length (500 words ~= 1 page)
            word_count = len(text.split())
            page_count = max(1, word_count // 500)
            return text, page_count

        else:
            logger.warning(f"Unsupported file type for text extraction: {mime_type}")
            return "", 0

    except Exception as e:
        logger.error(f"Error extracting text from document: {str(e)}")
        raise


def calculate_risk_score(analysis_result: Dict[str, Any]) -> int:
    """
    Calculate numerical risk score (0-100) based on analysis results with wide distribution

    Scoring algorithm (highly granular to prevent clustering at 100):
    - Base score: 0 (no risk)
    - +10 points per critical red flag (major legal/compliance issues)
    - +6 points per high-severity red flag (significant contractual concerns)
    - +3 points per medium red flag (notable but manageable issues)
    - +1 point per yellow flag (minor concerns worth noting)
    - Round to nearest 5
    - Cap at 100

    Risk Level Thresholds:
    - High: 50+ (5+ critical flags, or 8+ high flags, or mix of significant issues)
    - Medium: 20-49 (2-4 critical flags, or 3-7 high flags, or multiple medium flags)
    - Low: 0-19 (mostly yellow/medium flags, 0-1 critical flags)

    Args:
        analysis_result: Parsed JSON from Claude analysis

    Returns:
        Risk score from 0-100
    """
    score = 0

    risk_assessment = analysis_result.get('risk_assessment', {})
    red_flags = risk_assessment.get('red_flags', [])
    yellow_flags = risk_assessment.get('yellow_flags', [])

    # Highly granular scoring for wide distribution across 0-100 range
    # Critical: +10 (down from 15) - need 10 critical flags to hit 100
    # High: +6 (down from 8) - need 16+ high flags to hit 100
    # Medium: +3 (down from 4) - need 33+ medium flags to hit 100
    # Yellow: +1 (down from 2) - need 100 yellow flags to hit 100
    for flag in red_flags:
        severity = flag.get('severity', 'medium')
        if severity == 'critical':
            score += 10
        elif severity == 'high':
            score += 6
        else:  # medium
            score += 3

    score += len(yellow_flags) * 1

    # Round to nearest 5 for cleaner scoring (0, 5, 10, 15, 20, etc.)
    score = round(score / 5) * 5

    return min(score, 100)  # Cap at 100


def determine_risk_level(risk_score: int, red_flags: list) -> str:
    """
    Determine categorical risk level based on score and flags

    Args:
        risk_score: Numerical risk score (0-100)
        red_flags: List of red flag issues

    Returns:
        'high', 'medium', or 'low'
    """
    # Any critical red flags = automatic high risk
    has_critical = any(flag.get('severity') == 'critical' for flag in red_flags)
    if has_critical:
        return 'high'

    # Score-based categorization
    if risk_score >= 50:
        return 'high'
    elif risk_score >= 20:
        return 'medium'
    else:
        return 'low'


async def classify_contract_with_router(
    contract_text: str,
    filename: str,
    counterparty_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Classify contract type using the router agent

    Args:
        contract_text: Full text of the contract
        filename: Original filename for reference
        counterparty_name: Optional counterparty name

    Returns:
        Classification result with contract type and confidence
    """
    logger.info(f"🔀 Classifying contract with router: {filename}")

    router_instructions, _ = load_system_instructions('router')  # Router doesn't use legal standards

    user_prompt = f"""Classify the following contract into one of the five categories: vendor, customer, employment, dpa, or general.

Contract Filename: {filename}"""

    if counterparty_name:
        user_prompt += f"\nCounterparty: {counterparty_name}"

    user_prompt += f"""

Contract Text:
{contract_text}

Please provide your classification in the JSON format specified in the system instructions.

CRITICAL: You MUST include a "confidence_score" field (integer 0-100) in your JSON response. Use the confidence scoring guidelines in the system instructions to determine the appropriate score based on signal strength."""

    try:
        # Call Claude API with router instructions (async)
        response = await get_anthropic_client().messages.create(
            model=ROUTER_MODEL,  # Configurable via ROUTER_MODEL env var
            max_tokens=2000,  # Classification needs less tokens
            system=router_instructions,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            temperature=ROUTER_TEMPERATURE  # Configurable via ROUTER_TEMPERATURE env var
        )

        # Extract JSON from response
        response_text = response.content[0].text

        # Parse JSON
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            json_text = response_text[json_start:json_end].strip()
        else:
            json_text = response_text.strip()

        classification_result = json.loads(json_text)

        classified_type = classification_result.get('classification', 'general')
        confidence = classification_result.get('confidence_score', 0)
        reasoning = classification_result.get('reasoning', 'No reasoning provided')
        key_signals = classification_result.get('key_signals', [])
        alt_classification = classification_result.get('alternative_classification')
        metadata = classification_result.get('document_metadata', {})

        logger.info(f"✅ Contract classified as: {classified_type.upper()} (confidence: {confidence}%)")
        logger.info(f"📋 Router reasoning: {reasoning}")
        logger.info(f"🔑 Key signals: {', '.join(key_signals)}")
        if alt_classification:
            logger.info(f"🔄 Alternative classification: {alt_classification}")
        if metadata:
            logger.info(f"📄 Document metadata: {metadata}")

        # Add model and temperature metadata to classification result
        classification_result['model_metadata'] = {
            'model': ROUTER_MODEL,
            'temperature': ROUTER_TEMPERATURE,
            'stage': 'classification'
        }
        logger.info(f"🤖 Model: {ROUTER_MODEL}, Temperature: {ROUTER_TEMPERATURE}")

        return classification_result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse router response as JSON: {str(e)}")
        logger.warning(f"Defaulting to 'general' classification")
        return {
            'classification': 'general',
            'confidence_score': 0,
            'reasoning': 'Failed to classify, defaulting to general',
            'key_signals': []
        }

    except Exception as e:
        logger.error(f"Error during router classification: {str(e)}")
        logger.warning(f"Defaulting to 'general' classification")
        return {
            'classification': 'general',
            'confidence_score': 0,
            'reasoning': f'Error during classification: {str(e)}',
            'key_signals': []
        }


async def analyze_contract_with_claude(
    contract_text: str,
    filename: str,
    contract_type: str,  # Now required, from router classification
    counterparty_name: Optional[str] = None,
    client_id: Optional[str] = None
) -> tuple[Dict[str, Any], list]:
    """
    Send contract to Claude for analysis using specialized system instructions

    Args:
        contract_text: Full text of the contract
        filename: Original filename for reference
        contract_type: Contract type from router (vendor/customer/employment/dpa/general)
        counterparty_name: Optional counterparty name
        client_id: Optional client ID for loading client-specific legal standards

    Returns:
        Tuple of (parsed JSON analysis result, list of legal standards used)
    """
    logger.info(f"📋 Analyzing {contract_type.upper()} contract with specialized agent: {filename}")

    # Load specialized system instructions based on contract type (with legal standards)
    try:
        specialized_instructions, standards_used = load_system_instructions(contract_type, client_id)
    except Exception as e:
        logger.warning(f"Failed to load specialized instructions for {contract_type}, using general: {str(e)}")
        specialized_instructions, standards_used = load_system_instructions('general', client_id)

    user_prompt = f"""Analyze the following {contract_type} contract and provide a comprehensive risk assessment.

Contract Filename: {filename}
Contract Type: {contract_type}"""

    if counterparty_name:
        user_prompt += f"\nCounterparty: {counterparty_name}"

    user_prompt += f"""

Contract Text:
{contract_text}

Please provide your analysis in the JSON format specified in the system instructions."""

    try:
        # Call Claude API with specialized system instructions (async)
        response = await get_anthropic_client().messages.create(
            model=ANALYSIS_MODEL,  # Configurable via ANALYSIS_MODEL env var
            max_tokens=16000,
            system=specialized_instructions,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            temperature=ANALYSIS_TEMPERATURE  # Configurable via ANALYSIS_TEMPERATURE env var
        )

        # Extract JSON from response
        response_text = response.content[0].text

        # Try to parse JSON from the response
        # Claude might wrap it in ```json blocks, so handle that
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            json_text = response_text[json_start:json_end].strip()
        else:
            json_text = response_text.strip()

        analysis_result = json.loads(json_text)
        logger.info(f"✅ Contract analysis completed: {filename}")

        # Add model and temperature metadata to analysis result
        analysis_result['model_metadata'] = {
            'model': ANALYSIS_MODEL,
            'temperature': ANALYSIS_TEMPERATURE,
            'stage': 'analysis',
            'contract_type': contract_type
        }
        logger.info(f"🤖 Model: {ANALYSIS_MODEL}, Temperature: {ANALYSIS_TEMPERATURE}")

        return analysis_result, standards_used

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response as JSON: {str(e)}")
        logger.error(f"Raw response: {response_text[:500]}...")
        raise Exception(f"Invalid JSON response from Claude: {str(e)}")

    except Exception as e:
        logger.error(f"Error during Claude API call: {str(e)}")
        raise


async def process_contract(document_id: str) -> Dict[str, Any]:
    """
    Main contract processing pipeline

    1. Fetch document from database
    2. Download file from Supabase storage
    3. Extract text from document
    4. Analyze with Claude using system instructions
    5. Calculate risk scores
    6. Store analysis in contract_analysis table
    7. Update document status

    Args:
        document_id: UUID of the document to process

    Returns:
        Contract analysis result
    """
    # Initialize performance timer
    perf_timer = PerformanceTimer(document_id)

    try:
        logger.info(f"🚀 Starting contract processing for document: {document_id}")
        await log_processing_step(document_id, 'initialization', 'started', 'Starting contract processing')

        # 1. Fetch document record
        perf_timer.start_stage('fetch_document')
        doc_result = await asyncio.to_thread(
            lambda: get_supabase_client().table('documents')
                .select('*')
                .eq('id', document_id)
                .single()
                .execute()
        )

        if not doc_result.data:
            raise Exception(f"Document not found: {document_id}")

        document = doc_result.data
        storage_path = document['storage_path']
        filename = document['filename']
        contract_type = document.get('contract_type')
        counterparty_name = document.get('counterparty_name')
        client_id = document.get('client_id')  # Extract client_id for legal standards
        perf_timer.end_stage('fetch_document')

        logger.info(f"Processing contract: {filename}")
        await log_processing_step(document_id, 'initialization', 'completed', f'Processing {filename}', {'filename': filename})

        # 2. Download file from Supabase storage
        await log_processing_step(document_id, 'file_download', 'started', 'Downloading contract from storage')
        perf_timer.start_stage('file_download')
        file_bytes = await asyncio.to_thread(
            lambda: get_supabase_client().storage.from_('documents').download(storage_path)
        )

        # Save temporarily for processing
        temp_file_path = f"/tmp/{document_id}_{filename}"
        with open(temp_file_path, 'wb') as f:
            f.write(file_bytes)
        perf_timer.end_stage('file_download', {'file_size_bytes': len(file_bytes), 'file_size_mb': round(len(file_bytes) / 1024 / 1024, 2)})
        await log_processing_step(document_id, 'file_download', 'completed', f'Downloaded {len(file_bytes)} bytes')

        # 3. Extract text from document
        await log_processing_step(document_id, 'text_extraction', 'started', 'Extracting text from PDF')
        perf_timer.start_stage('text_extraction')
        mime_type = document.get('mime_type', 'application/pdf')
        contract_text, page_count = extract_text_from_document(temp_file_path, mime_type)

        if not contract_text or len(contract_text) < 100:
            raise Exception(f"Failed to extract sufficient text from document (got {len(contract_text)} chars)")

        perf_timer.end_stage('text_extraction', {'text_length': len(contract_text), 'text_length_kb': round(len(contract_text) / 1024, 2), 'page_count': page_count})
        logger.info(f"Extracted {len(contract_text)} characters from {page_count} pages")
        await log_processing_step(document_id, 'text_extraction', 'completed', f'Extracted {len(contract_text)} characters')

        # 4a. ROUTER: Classify contract type
        await log_processing_step(document_id, 'router_classification', 'started', 'Classifying contract type')
        perf_timer.start_stage('router_classification')
        classification_result = await classify_contract_with_router(
            contract_text=contract_text,
            filename=filename,
            counterparty_name=counterparty_name
        )

        # Get classified contract type (override user-provided type if any)
        classified_type = classification_result.get('classification', 'general')
        classification_confidence = classification_result.get('confidence_score', 0)
        perf_timer.end_stage('router_classification', {'classified_type': classified_type, 'confidence': classification_confidence})

        logger.info(f"🔀 Router classification: {classified_type.upper()} (confidence: {classification_confidence}%)")
        await log_processing_step(
            document_id,
            'router_classification',
            'completed',
            f'Classified as {classified_type} ({classification_confidence}% confidence)',
            {'classification': classified_type, 'confidence': classification_confidence}
        )

        # Track router instruction version
        router_version = get_instruction_version('router', SYSTEM_INSTRUCTIONS_DIR)
        logger.info(f"📋 Router instructions version: {router_version}")

        # Save router classification immediately so it's visible in UI while analysis runs
        router_classification_data = {
            'classification': classified_type,
            'confidence_score': classification_confidence,
            'reasoning': classification_result.get('reasoning', ''),
            'key_signals': classification_result.get('key_signals', [])
        }

        # Create or update contract_analysis record with just router classification
        # This allows the Type column to populate before the sub-agent completes
        try:
            # Get router processing time
            router_time = perf_timer.timings.get('router_classification', {}).get('duration', 0)

            # Check if record already exists
            existing = await asyncio.to_thread(
                lambda: get_supabase_client().table('contract_analysis')
                    .select('id')
                    .eq('document_id', document_id)
                    .execute()
            )

            if existing.data and len(existing.data) > 0:
                # Update existing record with router classification
                await asyncio.to_thread(
                    lambda: get_supabase_client().table('contract_analysis')
                        .update({
                            'contract_type': classified_type,
                            'router_classification': classified_type,
                            'router_confidence_score': classification_confidence,
                            'router_reasoning': classification_result.get('reasoning', ''),
                            'router_key_signals': json.dumps(classification_result.get('key_signals', [])),
                            'router_instructions_version': router_version,
                            'full_analysis': json.dumps({'router_classification': router_classification_data}),
                            'review_status': 'final_analysis',  # Router complete, detailed analysis in progress
                            'router_processing_seconds': round(router_time, 2)
                        })
                        .eq('document_id', document_id)
                        .execute()
                )
            else:
                # Create new record with router classification only
                await asyncio.to_thread(
                    lambda: get_supabase_client().table('contract_analysis')
                        .insert({
                            'document_id': document_id,
                            'contract_type': classified_type,
                            'router_classification': classified_type,
                            'router_confidence_score': classification_confidence,
                            'router_reasoning': classification_result.get('reasoning', ''),
                            'router_key_signals': json.dumps(classification_result.get('key_signals', [])),
                            'router_instructions_version': router_version,
                            'full_analysis': json.dumps({'router_classification': router_classification_data}),
                            'review_status': 'final_analysis',  # Router complete, detailed analysis in progress
                            'router_processing_seconds': round(router_time, 2)
                        })
                        .execute()
                )
            logger.info(f"✅ Router classification saved to database: {classified_type}")
        except Exception as e:
            logger.warning(f"⚠️ Could not save router classification early: {str(e)}")
            # Continue processing - this is non-critical

        # 4b. SPECIALIZED ANALYSIS: Analyze with appropriate specialized agent (with legal standards)
        await log_processing_step(document_id, 'contract_analysis', 'started', f'Analyzing {classified_type} contract with Claude')
        perf_timer.start_stage(f'specialized_analysis_{classified_type}')
        analysis_result, standards_used = await analyze_contract_with_claude(
            contract_text=contract_text,
            filename=filename,
            contract_type=classified_type,  # Use router classification
            counterparty_name=counterparty_name,
            client_id=client_id  # Pass client_id for legal standards loading
        )
        perf_timer.end_stage(f'specialized_analysis_{classified_type}', {'agent_type': classified_type, 'standards_count': len(standards_used)})
        await log_processing_step(document_id, 'contract_analysis', 'completed', 'Contract analysis completed')

        # Track sub-agent instruction version
        analysis_version = get_instruction_version(classified_type, SYSTEM_INSTRUCTIONS_DIR)
        logger.info(f"📋 Analysis instructions version ({classified_type}): {analysis_version}")

        # Track legal standards version
        standards_version = get_legal_standards_version(standards_used)
        logger.info(f"📋 Legal standards version: {standards_version}")

        # Add router classification to analysis result
        analysis_result['router_classification'] = {
            'classification': classified_type,
            'confidence_score': classification_confidence,
            'reasoning': classification_result.get('reasoning', ''),
            'key_signals': classification_result.get('key_signals', []),
            'model_metadata': classification_result.get('model_metadata', {})
        }

        # 5. Calculate risk scores
        risk_assessment = analysis_result.get('risk_assessment', {})
        red_flags = risk_assessment.get('red_flags', [])
        yellow_flags = risk_assessment.get('yellow_flags', [])

        risk_score = calculate_risk_score(analysis_result)
        overall_risk_level = determine_risk_level(risk_score, red_flags)

        # IMPORTANT: Always use calculated risk_level based on risk_score
        # Do NOT trust Claude's overall_risk_level as it may not match our scoring algorithm
        # The risk_level is determined by our scoring thresholds:
        #   High: score >= 50
        #   Medium: 20 <= score < 50
        #   Low: score < 20

        # Ensure overall_risk_level is never null (fallback to 'medium' if somehow empty)
        if not overall_risk_level:
            overall_risk_level = 'medium'
            logger.warning(f"overall_risk_level was null/empty, defaulting to 'medium'")

        # 6. Prepare data for contract_analysis table
        contract_metadata = analysis_result.get('contract_metadata', {})
        key_terms = analysis_result.get('key_terms', {})
        human_review = analysis_result.get('human_review_required', {})

        # Validate confidence_score (must be integer 0-100)
        confidence_score_raw = analysis_result.get('confidence_score', 85)
        confidence_score = 85  # default
        if isinstance(confidence_score_raw, (int, float)):
            confidence_score = max(0, min(100, int(confidence_score_raw)))
        elif isinstance(confidence_score_raw, str):
            try:
                confidence_score = max(0, min(100, int(float(confidence_score_raw))))
            except ValueError:
                logger.warning(f"Could not parse confidence_score: {confidence_score_raw}, using default 85")
                confidence_score = 85

        # Parse total_value to handle non-numeric values from Claude
        total_value_raw = contract_metadata.get('total_value')
        total_value = None
        if total_value_raw:
            # Try to extract numeric value if it's a string
            if isinstance(total_value_raw, str):
                # Remove common currency symbols and commas
                import re
                numeric_match = re.search(r'[\d,]+(?:\.\d+)?', total_value_raw.replace(',', ''))
                if numeric_match:
                    try:
                        total_value = float(numeric_match.group())
                    except ValueError:
                        logger.warning(f"Could not parse total_value: {total_value_raw}")
                        total_value = None
            elif isinstance(total_value_raw, (int, float)):
                total_value = float(total_value_raw)

        # Parse effective_date to handle non-date values from Claude
        effective_date_raw = contract_metadata.get('effective_date')
        effective_date = None
        if effective_date_raw:
            # Only accept valid date formats (YYYY-MM-DD or similar)
            if isinstance(effective_date_raw, str):
                import re
                from datetime import datetime
                # Try to parse common date formats
                date_patterns = [
                    r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
                    r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
                    r'\d{2}-\d{2}-\d{4}',  # MM-DD-YYYY
                ]
                for pattern in date_patterns:
                    match = re.search(pattern, effective_date_raw)
                    if match:
                        try:
                            # Try to parse the matched date
                            date_str = match.group()
                            if '-' in date_str and len(date_str.split('-')[0]) == 4:
                                # YYYY-MM-DD format
                                effective_date = date_str
                                break
                            # Other formats - convert to YYYY-MM-DD
                            # This is a simple check; add more parsing if needed
                        except Exception:
                            pass
                if not effective_date:
                    logger.warning(f"Could not parse effective_date: {effective_date_raw}")

        analysis_record = {
            'document_id': document_id,

            # Contract metadata (use router classification)
            'contract_type': classified_type,  # Router classification takes precedence
            'parties': json.dumps(contract_metadata.get('parties', [])),
            'effective_date': effective_date,  # Validated date or None
            'term_length': contract_metadata.get('term_length'),
            'total_value': total_value,

            # Router classification (dedicated columns for easy querying)
            'router_classification': classified_type,
            'router_confidence_score': classification_confidence,
            'router_reasoning': classification_result.get('reasoning', ''),
            'router_key_signals': json.dumps(classification_result.get('key_signals', [])),

            # System instruction versions (for re-running analyses when instructions change)
            'router_instructions_version': router_version,
            'analysis_instructions_version': analysis_version,
            'legal_standards_version': standards_version,

            # Key terms (JSONB)
            'ip_rights': json.dumps(key_terms.get('ip_rights', {})),
            'liability_terms': json.dumps(key_terms.get('liability', {})),
            'termination_terms': json.dumps(key_terms.get('termination', {})),
            'data_handling': json.dumps(key_terms.get('data_handling', {})),
            'payment_terms': json.dumps(key_terms.get('payment_terms', {})),

            # Risk assessment
            'overall_risk_level': overall_risk_level,
            'risk_score': risk_score,
            'red_flags': json.dumps(red_flags),
            'yellow_flags': json.dumps(yellow_flags),

            # Human review flags
            'human_review_required': human_review.get('required', False),
            'human_review_reasons': json.dumps(human_review.get('reasons', [])),
            'human_review_questions': json.dumps(human_review.get('specific_questions', [])),
            'human_review_priority': human_review.get('priority', 'normal'),

            # Summary and recommendations
            'executive_summary': analysis_result.get('executive_summary'),
            'recommendations': json.dumps(analysis_result.get('recommendations', [])),
            'confidence_score': confidence_score,  # Validated integer 0-100

            # Full analysis for audit trail (includes router classification)
            'full_analysis': json.dumps(analysis_result),

            # Review status - mark as completed now that full analysis is done
            'review_status': 'completed',  # Full analysis complete, ready for human review

            # Performance metrics
            'processing_time_seconds': round(perf_timer.get_total_time(), 2),
            'analysis_processing_seconds': round(perf_timer.timings.get(f'specialized_analysis_{classified_type}', {}).get('duration', 0), 2)
        }

        # 7. Store analysis in database
        # Use upsert to handle the case where router classification already created a record
        perf_timer.start_stage('database_save')
        await log_processing_step(document_id, 'saving_results', 'started', 'Saving analysis to database')
        insert_result = await asyncio.to_thread(
            lambda: get_supabase_client().table('contract_analysis')
                .upsert(analysis_record, on_conflict='document_id')
                .execute()
        )

        # 8. Update document status
        await asyncio.to_thread(
            lambda: get_supabase_client().table('documents')
                .update({
                    'processed': True,
                    'processing_status': 'completed',
                    'page_count': page_count
                })
                .eq('id', document_id)
                .execute()
        )
        await log_processing_step(document_id, 'saving_results', 'completed', f'Analysis saved - Risk: {overall_risk_level} ({risk_score}/100)')
        perf_timer.end_stage('database_save')

        # Cleanup temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        # Log performance summary
        total_time = perf_timer.get_total_time()
        perf_summary = perf_timer.get_summary()

        logger.info(f"✅ Contract analysis completed and saved: {document_id}")
        logger.info(f"   Risk Level: {overall_risk_level.upper()} ({risk_score}/100)")
        logger.info(f"   Human Review Required: {human_review.get('required', False)}")
        logger.info(f"🏁 TOTAL PROCESSING TIME: {total_time:.2f}s")
        logger.info(f"📊 PERFORMANCE BREAKDOWN:")

        # Sort stages by duration (longest first)
        sorted_stages = sorted(
            perf_summary['stages'].items(),
            key=lambda x: x[1]['duration'],
            reverse=True
        )

        for stage_name, stage_data in sorted_stages:
            metadata_str = ""
            if stage_data.get('metadata'):
                metadata_str = f" | {stage_data['metadata']}"
            logger.info(
                f"   - {stage_name}: {stage_data['duration']:.2f}s "
                f"({stage_data['percentage']:.1f}%){metadata_str}"
            )

        return insert_result.data[0]

    except Exception as e:
        logger.error(f"❌ Error processing contract {document_id}: {str(e)}")
        await log_processing_step(document_id, 'error', 'failed', f'Processing failed: {str(e)[:200]}', {'error': str(e)})

        # Update document with error status
        try:
            await asyncio.to_thread(
                lambda: get_supabase_client().table('documents')
                    .update({
                        'processed': False,
                        'processing_status': f'error: {str(e)[:200]}',
                        'error_message': str(e)  # Store full error message for UI display
                    })
                    .eq('id', document_id)
                    .execute()
            )
        except:
            pass

        # DON'T raise - this would block BackgroundTasks queue
        # Error is already logged and database is updated
        logger.error(f"Contract processing failed but not raising to avoid blocking queue: {document_id}")
