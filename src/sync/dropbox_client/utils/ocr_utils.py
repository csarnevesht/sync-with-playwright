import mimetypes
import logging
import re
from pdf2image import convert_from_path
import pytesseract

COMPANY_WORDS = {
    'life', 'insurance', 'company', 'inc', 'llc', 'corp', 'corporation', 'trust', 'bank', 'financial', 'partners', 'group'
}
EXCLUSION_WORDS = COMPANY_WORDS | {
    'fixed', 'annuity', 'variable', 'premium', 'beneficiary', 'policy', 'owner', 'insured', 'joint', 'type', 'amount',
    'payment', 'interest', 'rate', 'application', 'date', 'number', 'address', 'city', 'state', 'zip', 'phone', 'email',
    'relationship', 'agent', 'signature', 'plan', 'account', 'contract', 'product', 'term', 'applicant', 'name', 'first', 'last', 'mi', 'middle', 'ssn', 'social', 'security', 'tin', 'dob', 'gender', 'mailing', 'residence', 'cannot', 'box', 'different', 'than', 'beneficiary', 'primary', 'contingent', 'entity', 'type', 'owner', 'joint', 'owner', 'insured', 'policyholder', 'city', 'state', 'zip', 'mailing', 'phone', 'number', 'dob', 'date', 'ssn', 'email', 'residence', 'cannot', 'box', 'different', 'than', 'agent', 'signature', 'plan', 'account', 'contract', 'product', 'term', 'application', 'date', 'number', 'address', 'city', 'state', 'zip', 'phone', 'email', 'relationship', 'agent', 'signature', 'plan', 'account', 'contract', 'product', 'term'
}

def is_likely_non_person(name):
    words = set(name.lower().split())
    # If all words are in the exclusion list, or any word is in the exclusion list and there are only two words, skip
    return all(word in EXCLUSION_WORDS for word in words) or (len(words) == 2 and any(word in EXCLUSION_WORDS for word in words))

def extract_name_with_ocr_with_conf(content: str, name_parts=None, file_name=None, logger=None):
    """
    Extract name information from file content using OCR and return confidence.
    Args:
        content (str): Path to the PDF file.
        name_parts (dict, optional): Name parts for matching (e.g., {'last_name': 'Smith'}).
        file_name (str, optional): File name for logging.
        logger (logging.Logger, optional): Logger instance.
    Returns:
        dict or None: {'owner_data': {...}, 'avg_conf': float} or None
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    try:
        # Check if the file is a valid PDF before attempting OCR
        mime_type, _ = mimetypes.guess_type(content)
        logger.info(f"[OCR] File path: {content}, Detected MIME type: {mime_type}")
        if not (mime_type and mime_type.lower() == 'application/pdf'):
            logger.error(f"[OCR] File is not a valid PDF: BEGIN CONTENT {content} END CONTENT. Skipping OCR extraction.")
            return None

        # Convert PDF to images with higher DPI and larger size for better text recognition
        try:
            images = convert_from_path(
                content,
                dpi=600,  # Increased DPI for better quality
                size=(2000, None)  # Wider width to capture longer lines
            )
        except Exception as pdf_exc:
            logger.error(f"[OCR] Failed to convert PDF to images: {pdf_exc}")
            return None

        ocr_lines = []
        confidences = []
        for image in images:
            # Use pytesseract to get confidence scores
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            for i, text in enumerate(ocr_data['text']):
                if text.strip():
                    ocr_lines.append(text)
                    conf = ocr_data['conf'][i]
                    if conf != '-1':
                        try:
                            confidences.append(int(conf))
                        except ValueError:
                            pass
            # Also add splitlines for compatibility with old logic
            ocr_lines.extend(pytesseract.image_to_string(image).splitlines())

        # Heuristic: check average confidence
        avg_conf = sum(confidences) / len(confidences) if confidences else 0
        logger.info(f"[OCR] Average Tesseract confidence: {avg_conf:.2f}")
        if avg_conf < 60:
            logger.info("[OCR] Low average confidence detected; this file is likely handwritten or of poor quality.")
        else:
            logger.info("[OCR] Average confidence suggests mostly printed or high-quality text.")

        # First strategy: Look for OWNER section, then 'Name: First MI Last' header, then extract the next line(s) as the name
        for i, line in enumerate(ocr_lines):
            logger.debug(f"[OWNER] Checking line {i}: '{line}'")
            if 'OWNER' in line.upper():
                # Look for the table header in the next few lines
                for j in range(i+1, min(i+6, len(ocr_lines))):
                    header = ocr_lines[j]
                    if 'Name:' in header and 'First' in header and 'Last' in header:
                        # The next line(s) should be the actual name row
                        if j+1 < len(ocr_lines):
                            name_row = ocr_lines[j+1].strip()
                            name_parts_row = name_row.split()
                            # If only one word, check the next line for the last name
                            if len(name_parts_row) == 1 and (j+2) < len(ocr_lines):
                                next_row = ocr_lines[j+2].strip()
                                next_parts = next_row.split()
                                if len(next_parts) == 1:
                                    result = {
                                        'first_name': name_parts_row[0],
                                        'last_name': next_parts[0]
                                    }
                                    if is_likely_non_person(f"{result['first_name']} {result['last_name']}"):
                                        logger.info(f"[OWNER TABLE] Skipping non-person name: '{result['first_name']} {result['last_name']}'")
                                        continue
                                    logger.info(f"[OWNER TABLE] Extracted split name: {result}")
                                    return {
                                        'owner_data': result,
                                        'avg_conf': avg_conf
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
                                logger.info(f"[OWNER TABLE] Extracted name: {result}")
                                return {
                                    'owner_data': result,
                                    'avg_conf': avg_conf
                                }

        # 2. Look for 'Full Name' marker and extract the next non-empty line
        for i, line in enumerate(ocr_lines):
            logger.debug(f"[Full Name] Checking line {i}: '{line}'")
            if 'Full Name' in line:
                # Look for the next non-empty line
                for j in range(i+1, min(i+5, len(ocr_lines))):
                    candidate = ocr_lines[j].strip()
                    logger.debug(f"[Full Name] Candidate after marker: '{candidate}'")
                    if candidate and len(candidate.split()) >= 2:
                        name_parts_row = candidate.split()
                        if name_parts and any(part.lower() in name_parts.get('last_name', '').lower() for part in name_parts_row):
                            full_name = f"{' '.join(name_parts_row)}"
                            if is_likely_non_person(full_name):
                                logger.info(f"[Full Name] Skipping non-person name: '{full_name}'")
                                continue
                            logger.info(f"[Full Name] Found name after marker: {candidate}")
                            # Find the index of the part containing the last name
                            last_name_index = next(i for i, part in enumerate(name_parts_row) 
                                                    if part.lower() in name_parts.get('last_name', '').lower())
                            # Use all parts up to and including the last name as the last name
                            last_name = ' '.join(name_parts_row[last_name_index:])
                            first_name = ' '.join(name_parts_row[:last_name_index])
                            return {
                                'owner_data': {
                                    'first_name': first_name,
                                    'last_name': last_name
                                },
                                'avg_conf': avg_conf
                            }

        # 3. Fallback: Any line containing the last name and at least two words
        for i, line in enumerate(ocr_lines):
            logger.debug(f"[Last Name Fallback] Checking line {i}: '{line}'")
            if name_parts and name_parts.get('last_name', '').lower() in line.lower():
                words = line.strip().split()
                if len(words) >= 2:
                    full_name = f"{' '.join(words)}"
                    if is_likely_non_person(full_name):
                        logger.info(f"[Last Name Fallback] Skipping non-person name: '{full_name}'")
                        continue
                    logger.info(f"[Last Name Fallback] Found line with last name: {line}")
                    return {
                        'owner_data': {
                            'first_name': words[0],
                            'last_name': words[-1]
                        },
                        'avg_conf': avg_conf
                    }

        # 4. Try previous patterns
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
                    if is_likely_non_person(name):
                        logger.info(f"[Pattern] Skipping non-person name: '{name}'")
                        continue
                    logger.info(f"[Pattern] Found potential name match: '{name}'")
                    name_parts_row = re.split(r'\s+', name)
                    if len(name_parts_row) >= 2:
                        if name_parts and any(part.lower() in name_parts.get('last_name', '').lower() for part in name_parts_row):
                            logger.info(f"[Pattern] Found name with matching last name: {name}")
                            return {
                                'owner_data': {
                                    'first_name': name_parts_row[0],
                                    'last_name': name_parts_row[-1]
                                },
                                'avg_conf': avg_conf
                            }
                        elif all(word[0].isupper() for word in name_parts_row):
                            logger.info(f"[Pattern] Found name without matching last name: {name}")
                            return {
                                'owner_data': {
                                    'first_name': name_parts_row[0],
                                    'last_name': name_parts_row[-1]
                                },
                                'avg_conf': avg_conf
                            }

        # 5. Fallback: two consecutive capitalized words
        for line in ocr_lines:
            words = re.split(r'\s+', line.strip())
            if len(words) >= 2:
                for i in range(len(words) - 1):
                    if (words[i][0].isupper() and words[i+1][0].isupper() and
                        len(words[i]) > 1 and len(words[i+1]) > 1):
                        potential_name = f"{words[i]} {words[i+1]}"
                        if is_likely_non_person(potential_name):
                            logger.info(f"[CapWords] Skipping non-person name: '{potential_name}'")
                            continue
                        logger.info(f"[CapWords] Found potential name from capitalized words: '{potential_name}'")
                        if name_parts and any(word.lower() in name_parts.get('last_name', '').lower() for word in words):
                            logger.info(f"[CapWords] Found name with matching last name: {potential_name}")
                            return {
                                'owner_data': {
                                    'first_name': words[i],
                                    'last_name': words[i+1]
                                },
                                'avg_conf': avg_conf
                            }

        return None
    except Exception as e:
        import traceback
        logger.error(f"Error during OCR name extraction: {str(e)}\n{traceback.format_exc()}")
        return None 