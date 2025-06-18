import mimetypes
import logging
import re
from pdf2image import convert_from_path
import numpy as np
import easyocr
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import torch

COMPANY_WORDS = {
    'life', 'insurance', 'company', 'inc', 'llc', 'corp', 'corporation', 'trust', 'bank', 'financial', 'partners', 'group'
}
EXCLUSION_WORDS = COMPANY_WORDS | {
    'fixed', 'annuity', 'variable', 'premium', 'beneficiary', 'policy', 'owner', 'insured', 'joint', 'type', 'amount',
    'payment', 'interest', 'rate', 'application', 'date', 'number', 'address', 'city', 'state', 'zip', 'phone', 'email',
    'relationship', 'agent', 'signature', 'plan', 'account', 'contract', 'product', 'term', 'applicant', 'name', 'first', 'last', 'mi', 'middle', 'ssn', 'social', 'security', 'tin', 'dob', 'gender', 'mailing', 'residence', 'cannot', 'box', 'different', 'than', 'beneficiary', 'primary', 'contingent', 'entity', 'type', 'owner', 'joint', 'owner', 'insured', 'policyholder', 'city', 'state', 'zip', 'mailing', 'phone', 'number', 'dob', 'date', 'ssn', 'email', 'residence', 'cannot', 'box', 'different', 'than', 'agent', 'signature', 'plan', 'account', 'contract', 'product', 'term', 'application', 'date', 'number', 'address', 'city', 'state', 'zip', 'phone', 'email', 'relationship', 'agent', 'signature', 'plan', 'account', 'contract', 'product', 'term',
    'oi', 'qualified', 'transfer', 'sep', 'ira', 'roth', 'traditional', 'exchange', 'contribution', 'payment', 'type', 'nonqualified', 'partial', 'estimated', 'rollover', 'amount', 'enclosed', 'for', 'tax', 'year', 'series', 'spda', 'gro', 'mva', 'disclosure', 'periods', 'interest', 'rate', 'guarantee', 'new', 'momentum', 'check', 'one'
}

COMMON_NON_PERSON_NAMES = {
    'the annuitant', 'annuitant', 'owner', 'joint owner', 'insured', 'policyholder',
    'applicant', 'trustee', 'agent', 'signature', 'witness', 'grantor', 'beneficiary',
    'entity', 'company', 'insurance company', 'financial group', 'escrow', 'trust',
    'notary', 'public', 'authorized individual', 'print name', 'signature', 'date signed',
    'mailing instructions', 'fixed annuity', 'variable annuity', 'new momentum', 'spda series ii',
    'integrity life', 'insurance company', 'financial group', 'corporation', 'llc', 'inc', 'corp',
    'page', 'form', 'application', 'type', 'amount', 'payment', 'interest', 'rate', 'date', 'number',
    'address', 'city', 'state', 'zip', 'phone', 'email', 'relationship', 'plan', 'account', 'contract',
    'product', 'term', 'primary', 'contingent', 'entity', 'type', 'owner', 'joint', 'insured', 'policyholder',
    'city', 'state', 'zip', 'mailing', 'phone', 'number', 'dob', 'date', 'ssn', 'email', 'residence', 'cannot',
    'box', 'different', 'than', 'agent', 'signature', 'plan', 'account', 'contract', 'product', 'term',
    'qualified', 'transfer', 'sep', 'ira', 'roth', 'traditional', 'exchange', 'contribution', 'payment', 'type',
    'nonqualified', 'partial', 'estimated', 'rollover', 'amount', 'enclosed', 'for', 'tax', 'year', 'series',
    'spda', 'gro', 'mva', 'disclosure', 'periods', 'interest', 'rate', 'guarantee', 'new', 'momentum', 'check', 'one'
}

# Load TrOCR model and processor once
TROCR_PROCESSOR = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
TROCR_MODEL = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")

def is_likely_non_person(name):
    words = name.split()
    words_set = set(w.lower() for w in words)
    name_lc = name.strip().lower()
    if name_lc in COMMON_NON_PERSON_NAMES:
        return True
    if all(word in EXCLUSION_WORDS for word in words_set) or (len(words_set) == 2 and any(word in EXCLUSION_WORDS for word in words_set)):
        return True
    if any(len(word) < 2 and not (len(word) == 1 and word.isupper()) for word in words):
        return True
    if all(word.isupper() for word in words) or all(word.islower() for word in words):
        return True
    if any(not (word.isalpha() or (len(word) == 2 and word[1] == '.' and word[0].isupper())) for word in words):
        return True
    return False

def extract_annuitant_info_from_lines(ocr_lines):
    info = {}
    for i, line in enumerate(ocr_lines):
        l = line.lower()
        logging.info(f"[ANN_INFO] Line {i}: '{line}'")
        if 'name' in l and 'first' in l and 'last' in l:
            if i+1 < len(ocr_lines):
                name_line = ocr_lines[i+1].strip()
                name_parts = name_line.split()
                logging.info(f"[ANN_INFO] Candidate name line: '{name_line}' (line {i+1})")
                if len(name_parts) >= 2:
                    info['first_name'] = name_parts[0]
                    info['last_name'] = name_parts[-1]
                    logging.info(f"[ANN_INFO] Extracted name: {info['first_name']} {info['last_name']}")
        if 'address' in l and 'city' not in l:
            if i+1 < len(ocr_lines):
                address = ocr_lines[i+1].strip()
                info['address'] = address
                logging.info(f"[ANN_INFO] Extracted address: {address}")
        if 'city' in l and 'state' in l and 'zip' in l:
            if i+1 < len(ocr_lines):
                city_state_zip = ocr_lines[i+1].strip().split()
                logging.info(f"[ANN_INFO] Candidate city/state/zip line: '{ocr_lines[i+1].strip()}' (line {i+1})")
                if len(city_state_zip) >= 3:
                    info['city'] = city_state_zip[0]
                    info['state'] = city_state_zip[1]
                    info['zip'] = city_state_zip[2]
                    logging.info(f"[ANN_INFO] Extracted city/state/zip: {info['city']}, {info['state']}, {info['zip']}")
        if 'phone number' in l:
            match = re.search(r'\(?\d{3}\)\s*\d{3}-\d{4}', line)
            if match:
                info['phone_number'] = match.group(0)
                logging.info(f"[ANN_INFO] Extracted phone number: {info['phone_number']} from line {i}")
            elif i+1 < len(ocr_lines):
                phone = ocr_lines[i+1].strip()
                info['phone_number'] = phone
                logging.info(f"[ANN_INFO] Extracted phone number: {phone} from line {i+1}")
        if 'social security' in l or 'tin' in l:
            match = re.search(r'\d{3}-\d{2}-\d{4}', line)
            if match:
                info['ssn'] = match.group(0)
                logging.info(f"[ANN_INFO] Extracted SSN: {info['ssn']} from line {i}")
            elif i+1 < len(ocr_lines):
                ssn = ocr_lines[i+1].strip()
                info['ssn'] = ssn
                logging.info(f"[ANN_INFO] Extracted SSN: {ssn} from line {i+1}")
        if 'sex' in l:
            if 'female' in l and ('x' in l or '☑' in l or '✓' in l):
                info['sex'] = 'Female'
                logging.info(f"[ANN_INFO] Extracted sex: Female from line {i}")
            elif 'male' in l and ('x' in l or '☑' in l or '✓' in l):
                info['sex'] = 'Male'
                logging.info(f"[ANN_INFO] Extracted sex: Male from line {i}")
        if 'date of birth' in l:
            match = re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', line)
            if match:
                info['dob'] = match.group(0)
                logging.info(f"[ANN_INFO] Extracted DOB: {info['dob']} from line {i}")
            elif i+1 < len(ocr_lines):
                dob_line = ocr_lines[i+1].strip()
                match = re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', dob_line)
                if match:
                    info['dob'] = match.group(0)
                    logging.info(f"[ANN_INFO] Extracted DOB: {info['dob']} from line {i+1}")
        if 'state/country of birth' in l:
            if i+1 < len(ocr_lines):
                scob = ocr_lines[i+1].strip()
                info['state_country_of_birth'] = scob
                logging.info(f"[ANN_INFO] Extracted state/country of birth: {scob}")
    logging.info(f"[ANN_INFO] Final annuitant_info: {info}")
    return info

def extract_text_lines_with_easyocr(pdf_path, max_pages=5):
    images = convert_from_path(pdf_path, dpi=600, size=(2000, None))
    if max_pages is not None:
        images = images[:max_pages]
    reader = easyocr.Reader(['en'], gpu=False)
    ocr_lines = []
    confidences = []
    for page_num, image in enumerate(images):
        logging.info(f"[EASYOCR] Processing page {page_num+1}/{len(images)}")
        result = reader.readtext(np.array(image))
        page_lines = []
        page_confidences = []
        for bbox, text, conf in result:
            if text.strip():
                ocr_lines.append(text)
                confidences.append(conf)
                page_lines.append(text)
                page_confidences.append(conf)
        logging.info(f"[EASYOCR] Page {page_num+1}: {len(page_lines)} lines, confidences: {page_confidences}")
        logging.info(f"[EASYOCR] Page {page_num+1} lines: {page_lines}")
    logging.info(f"[EASYOCR] Total OCR lines: {len(ocr_lines)}")
    logging.info(f"[EASYOCR] Total confidences: {len(confidences)}")
    return ocr_lines, confidences

def extract_name_with_ocr_with_conf(content: str, name_parts=None, file_name=None, logger=None):
    """
    Extract name information from file content using EasyOCR and return confidence.
    Args:
        content (str): Path to the PDF file.
        name_parts (dict, optional): Name parts for matching (e.g., {'last_name': 'Smith'}).
        file_name (str, optional): File name for logging.
        logger (logging.Logger, optional): Logger instance.
    Returns:
        dict or None: {'owner_data': {...}, 'avg_conf': float, 'annuitant_info': {...}} or None
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    try:
        mime_type, _ = mimetypes.guess_type(content)
        logger.info(f"[OCR] File path: {content}, Detected MIME type: {mime_type}")
        if not (mime_type and mime_type.lower() == 'application/pdf'):
            logger.error(f"[OCR] File is not a valid PDF: BEGIN CONTENT {content} END CONTENT. Skipping OCR extraction.")
            return None

        ocr_lines, confidences = extract_text_lines_with_easyocr(content, max_pages=5)

        logger.info(f"[OCR] Number of OCR lines: {len(ocr_lines)}")
        logger.info(f"[OCR] Number of confidence scores: {len(confidences)}")
        logger.info(f"[OCR] First 10 OCR lines: {ocr_lines[:10]}")
        logger.info(f"[OCR] First 10 confidences: {confidences[:10]}")

        avg_conf = sum(confidences) / len(confidences) if confidences else 0
        logger.info(f"[OCR] Average EasyOCR confidence: {avg_conf:.2f}")
        if avg_conf < 60:
            logger.info("[OCR] Low average confidence detected; this file is likely handwritten or of poor quality.")
        else:
            logger.info("[OCR] Average confidence suggests mostly printed or high-quality text.")

        annuitant_info = extract_annuitant_info_from_lines(ocr_lines)

        # Existing name extraction logic (for backward compatibility)
        for i, line in enumerate(ocr_lines):
            logger.debug(f"[OWNER] Checking line {i}: '{line}'")
            if 'OWNER' in line.upper():
                for j in range(i+1, min(i+6, len(ocr_lines))):
                    header = ocr_lines[j]
                    if 'Name:' in header and 'First' in header and 'Last' in header:
                        if j+1 < len(ocr_lines):
                            name_row = ocr_lines[j+1].strip()
                            name_parts_row = name_row.split()
                            logger.info(f"[OWNER TABLE] Candidate name: '{name_row}' (line {j+1})")
                            if len(name_parts_row) == 1 and (j+2) < len(ocr_lines):
                                next_row = ocr_lines[j+2].strip()
                                next_parts = next_row.split()
                                logger.info(f"[OWNER TABLE] Candidate split name: '{name_parts_row[0]} {next_parts[0]}' (lines {j+1}, {j+2})")
                                if len(next_parts) == 1:
                                    result = {
                                        'first_name': name_parts_row[0],
                                        'last_name': next_parts[0]
                                    }
                                    if is_likely_non_person(f"{result['first_name']} {result['last_name']}"):
                                        logger.info(f"[OWNER TABLE] Skipping non-person name: '{result['first_name']} {result['last_name']}'")
                                        continue
                                    logger.info(f"[OWNER TABLE] Accepted split name: {result}")
                                    return {
                                        'owner_data': result,
                                        'avg_conf': avg_conf,
                                        'annuitant_info': annuitant_info
                                    }
                            elif len(name_parts_row) >= 2:
                                result = {
                                    'first_name': name_parts_row[0],
                                    'last_name': name_parts_row[-1]
                                }
                                if len(name_parts_row) == 3:
                                    result['middle_initial'] = name_parts_row[1]
                                if is_likely_non_person(f"{result['first_name']} {result['last_name']}"):
                                    logger.info(f"[OWNER TABLE] Skipping non-person name: '{result['first_name']} {result['last_name']}'")
                                    continue
                                logger.info(f"[OWNER TABLE] Accepted name: {result}")
                                return {
                                    'owner_data': result,
                                    'avg_conf': avg_conf,
                                    'annuitant_info': annuitant_info
                                }

        for i, line in enumerate(ocr_lines):
            logger.debug(f"[Full Name] Checking line {i}: '{line}'")
            if 'Full Name' in line:
                for j in range(i+1, min(i+5, len(ocr_lines))):
                    candidate = ocr_lines[j].strip()
                    logger.info(f"[Full Name] Candidate after marker: '{candidate}' (line {j})")
                    if candidate and len(candidate.split()) >= 2:
                        name_parts_row = candidate.split()
                        if name_parts and any(part.lower() in name_parts.get('last_name', '').lower() for part in name_parts_row):
                            full_name = f"{' '.join(name_parts_row)}"
                            if is_likely_non_person(full_name):
                                logger.info(f"[Full Name] Skipping non-person name: '{full_name}'")
                                continue
                            logger.info(f"[Full Name] Accepted name after marker: {candidate}")
                            last_name_index = next(i for i, part in enumerate(name_parts_row) 
                                                    if part.lower() in name_parts.get('last_name', '').lower())
                            last_name = ' '.join(name_parts_row[last_name_index:])
                            first_name = ' '.join(name_parts_row[:last_name_index])
                            return {
                                'owner_data': {
                                    'first_name': first_name,
                                    'last_name': last_name
                                },
                                'avg_conf': avg_conf,
                                'annuitant_info': annuitant_info
                            }

        for i, line in enumerate(ocr_lines):
            logger.debug(f"[Last Name Fallback] Checking line {i}: '{line}'")
            if name_parts and name_parts.get('last_name', '').lower() in line.lower():
                words = line.strip().split()
                logger.info(f"[Last Name Fallback] Candidate: '{' '.join(words)}' (line {i})")
                if len(words) >= 2:
                    full_name = f"{' '.join(words)}"
                    if is_likely_non_person(full_name):
                        logger.info(f"[Last Name Fallback] Skipping non-person name: '{full_name}'")
                        continue
                    logger.info(f"[Last Name Fallback] Accepted line with last name: {line}")
                    return {
                        'owner_data': {
                            'first_name': words[0],
                            'last_name': words[-1]
                        },
                        'avg_conf': avg_conf,
                        'annuitant_info': annuitant_info
                    }

        name_patterns = [
            r'Name\s*:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'Applicant\s*:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'Insured\s*:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'Policyholder\s*:\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s*$',
            r'^([A-Z][a-z]+\s+[A-Z][a-z]+)\s*',
        ]
        for line in ocr_lines:
            logger.debug(f"[Pattern] Checking line for name: '{line}'")
            for pattern in name_patterns:
                match = re.search(pattern, line)
                if match:
                    name = match.group(1).strip()
                    logger.info(f"[Pattern] Candidate: '{name}' (pattern: {pattern})")
                    if is_likely_non_person(name):
                        logger.info(f"[Pattern] Skipping non-person name: '{name}'")
                        continue
                    logger.info(f"[Pattern] Accepted potential name match: '{name}'")
                    name_parts_row = re.split(r'\s+', name)
                    if len(name_parts_row) >= 2:
                        if name_parts and any(part.lower() in name_parts.get('last_name', '').lower() for part in name_parts_row):
                            logger.info(f"[Pattern] Found name with matching last name: {name}")
                            return {
                                'owner_data': {
                                    'first_name': name_parts_row[0],
                                    'last_name': name_parts_row[-1]
                                },
                                'avg_conf': avg_conf,
                                'annuitant_info': annuitant_info
                            }
                        elif all(word[0].isupper() for word in name_parts_row):
                            logger.info(f"[Pattern] Found name without matching last name: {name}")
                            return {
                                'owner_data': {
                                    'first_name': name_parts_row[0],
                                    'last_name': name_parts_row[-1]
                                },
                                'avg_conf': avg_conf,
                                'annuitant_info': annuitant_info
                            }

        for line in ocr_lines:
            words = re.split(r'\s+', line.strip())
            if len(words) >= 2:
                for i in range(len(words) - 1):
                    if (words[i][0].isupper() and words[i+1][0].isupper() and
                        len(words[i]) > 1 and len(words[i+1]) > 1):
                        potential_name = f"{words[i]} {words[i+1]}"
                        logger.info(f"[CapWords] Candidate: '{potential_name}' (words {i}, {i+1})")
                        if is_likely_non_person(potential_name):
                            logger.info(f"[CapWords] Skipping non-person name: '{potential_name}'")
                            continue
                        logger.info(f"[CapWords] Accepted potential name from capitalized words: '{potential_name}'")
                        if name_parts and any(word.lower() in name_parts.get('last_name', '').lower() for word in words):
                            logger.info(f"[CapWords] Found name with matching last name: {potential_name}")
                            return {
                                'owner_data': {
                                    'first_name': words[i],
                                    'last_name': words[i+1]
                                },
                                'avg_conf': avg_conf,
                                'annuitant_info': annuitant_info
                            }

        if annuitant_info:
            logger.info("[OCR] No person name found, returning annuitant_info as fallback.")
            return {
                'owner_data': None,
                'avg_conf': avg_conf,
                'annuitant_info': annuitant_info
            }
        logger.info("[OCR] No owner or annuitant name could be extracted from OCR lines.")
        return None
    except Exception as e:
        import traceback
        logger.error(f"Error during OCR name extraction: {str(e)}\n{traceback.format_exc()}")
        return None

def extract_text_with_trocr(image: Image.Image, device: str = None) -> str:
    """
    Run TrOCR on a PIL image and return the recognized text.
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    TROCR_MODEL.to(device)
    pixel_values = TROCR_PROCESSOR(images=image, return_tensors="pt").pixel_values.to(device)
    generated_ids = TROCR_MODEL.generate(pixel_values)
    text = TROCR_PROCESSOR.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return text.strip() 