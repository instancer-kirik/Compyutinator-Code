import re

def detect_sensitive_info(text: str) -> bool:
    """Detect if the text contains sensitive information."""
    # Define regex patterns for sensitive information
    patterns = {
        "credit_card": r'\b(?:\d[ -]*?){13,16}\b',  # Basic credit card pattern
        "ssn": r'\b\d{3}-\d{2}-\d{4}\b',  # Social Security Number
        "email": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # Email address
        "phone": r'\b\d{3}[ -]?\d{3}[ -]?\d{4}\b'  # Phone number
    }

    for label, pattern in patterns.items():
        if re.search(pattern, text):
            print(f"Detected sensitive information: {label}")
            return True
    return False

# # Example usage
# text_to_check = "My credit card number is 1234-5678-9012-3456."
# if detect_sensitive_info(text_to_check):
#     print("Sensitive information detected. Masking will be applied.")
# else:
  #  print("No sensitive information detected.")
def mask_any_text(self, text: str):
    """Mask any text and display it if sensitive."""
    if detect_sensitive_info(text):
        masked_string = self.mask_text(text)
        self.display_masked_string(masked_string)
    else:
        self.display_masked_string(text)  # Display as is if not sensitive