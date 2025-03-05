import re

def format_response(text, context=None):
    """Format response for better readability with proper list handling"""
    if not text:
        return ""
    
    # First, identify and mark numbered lists to preserve them
    def preserve_lists(match):
        num, content = match.groups()
        # Mark this as a list item with a special token
        return f"__LIST_ITEM_{num}__ {content}"
    
    # Temporarily mark numbered list items
    text = re.sub(r'(?m)^(\d+)[.)] (.+)$', preserve_lists, text)
    
    # Process the text by splitting on periods that end sentences
    parts = re.split(r'(?<=[.!?])\s+', text)
    formatted_parts = []
    
    for part in parts:
        # Check if this is a marked list item
        if "__LIST_ITEM_" in part:
            # Restore the list format without adding extra newlines
            part = re.sub(r'__LIST_ITEM_(\d+)__ (.+)', r'\1. \2', part)
            formatted_parts.append(part)
        else:
            # Regular paragraph - add paragraph break
            formatted_parts.append("\n\n" + part)
    
    # Join parts and clean up
    result = ' '.join(formatted_parts).strip()
    
    # Clean up multiple spaces
    result = re.sub(r' {2,}', ' ', result)
    
    # Clean up multiple newlines
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    # Format bullet points consistently
    result = re.sub(r'(?m)^[-*•]\s*(.+)$', r'• \1', result)
    
    # Make sure numbered list items are well-formatted
    # Add proper newlines before each list item
    result = re.sub(r'(?<!\n)(\d+\. )', r'\n\1', result)
    
    # Format headings properly
    result = re.sub(r'(?m)^#+\s*(.+)$', r'## \1', result)
    
    return result