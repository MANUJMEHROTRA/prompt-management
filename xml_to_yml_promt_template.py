import re
import yaml
from lxml import etree
from lxml.etree import XMLSyntaxError
from io import StringIO

def fix_broken_tags(xml_content):
    """
    Fix common XML tag issues:
    1. Incorrect closing tags with wrong angle brackets (› instead of >)
    2. Missing closing tags
    3. Mismatched tags
    4. Improperly formatted list items
    """
    # Replace incorrect angle brackets
    xml_content = xml_content.replace("›", ">")
    
    # Fix common tag errors
    xml_content = re.sub(r'<([a-zA-Z0-9_]+)([^>]*)>([^<]*)<\/([a-zA-Z0-9_]+)([^>]*)>', 
                         lambda m: f"<{m.group(1)}{m.group(2)}>{m.group(3)}</{m.group(1)}>",
                         xml_content)
    
    # Fix <Example> tags
    xml_content = re.sub(r'</ Example>', '</Example>', xml_content)
    
    # Fix li tags
    xml_content = re.sub(r'‹li>', '<li>', xml_content)
    xml_content = re.sub(r'‹li\›', '<li>', xml_content)
    xml_content = re.sub(r'\\li>', '</li>', xml_content)
    xml_content = re.sub(r'‹/li>', '</li>', xml_content)
    
    # Fix ul tags
    xml_content = re.sub(r'‹ul>', '<ul>', xml_content)
    xml_content = re.sub(r'‹/ul>', '</ul>', xml_content)
    
    # Fix Example tags
    xml_content = re.sub(r'‹Example>', '<Example>', xml_content)
    xml_content = re.sub(r'‹/Example>', '</Example>', xml_content)
    xml_content = re.sub(r'</ Example>', '</Example>', xml_content)
    
    # Fix Example1 and Example2 tags
    xml_content = re.sub(r'‹Example1>', '<Example1>', xml_content)
    xml_content = re.sub(r'‹/Example1>', '</Example1>', xml_content)
    xml_content = re.sub(r'‹Example2>', '<Example2>', xml_content)
    xml_content = re.sub(r'‹/Example2>', '</Example2>', xml_content)
    
    # Fix transcript and output tags
    xml_content = re.sub(r'‹transcript>', '<transcript>', xml_content)
    xml_content = re.sub(r'‹output>', '<output>', xml_content)
    
    # Fix system instruction tag
    xml_content = re.sub(r'<system instruction>', '<system_instruction>', xml_content)
    xml_content = re.sub(r'</system instruction›', '</system_instruction>', xml_content)
    
    # Fix Task Instruction tag
    xml_content = re.sub(r'<Task Instruction>', '<Task_Instruction>', xml_content)
    xml_content = re.sub(r'</Task Instruction>', '</Task_Instruction>', xml_content)
    
    # Fix intent taxonomy tag
    xml_content = re.sub(r'‹intent taxonomy Instruction>', '<intent_taxonomy_Instruction>', xml_content)
    xml_content = re.sub(r'</intent taxonomy Instruction>', '</intent_taxonomy_Instruction>', xml_content)
    
    # Fix intent taxonomy list tag
    xml_content = re.sub(r'<intent taxonomy list>', '<intent_taxonomy_list>', xml_content)
    xml_content = re.sub(r'</intent taxonomy list>', '</intent_taxonomy_list>', xml_content)
    
    # Remove spurious backslashes
    xml_content = xml_content.replace("\\", "")
    
    # Fix other special characters
    xml_content = xml_content.replace("•..", "")
    
    return xml_content

def is_valid_xml(xml_content):
    """Check if XML is valid"""
    try:
        parser = etree.XMLParser(recover=True)
        etree.parse(StringIO(xml_content), parser)
        return True, ""
    except XMLSyntaxError as e:
        return False, str(e)

def xml_to_dict(xml_content):
    """Convert XML to Python dictionary"""
    parser = etree.XMLParser(recover=True)
    root = etree.fromstring(xml_content.encode(), parser)
    
    def element_to_dict(element):
        result = {}
        
        # Process text content
        if element.text and element.text.strip():
            text = element.text.strip()
            if not list(element):  # If no children elements
                return text
            else:
                result["_text"] = text
        
        # Process child elements
        for child in element:
            child_dict = element_to_dict(child)
            tag = child.tag
            
            # Handle multiple elements with the same tag
            if tag in result:
                if isinstance(result[tag], list):
                    result[tag].append(child_dict)
                else:
                    result[tag] = [result[tag], child_dict]
            else:
                result[tag] = child_dict
            
            # Process tail text if present
            if child.tail and child.tail.strip():
                if "_tail" not in result:
                    result["_tail"] = []
                result["_tail"].append(child.tail.strip())
        
        return result
    
    return element_to_dict(root)

def dict_to_yaml(data_dict):
    """Convert dictionary to YAML string"""
    return yaml.dump(data_dict, default_flow_style=False, sort_keys=False, allow_unicode=True)

def clean_dict(d):
    """Clean dictionary by removing unnecessary keys and normalizing values"""
    if isinstance(d, dict):
        # Remove internal keys
        result = {k: clean_dict(v) for k, v in d.items() if not k.startswith('_')}
        
        # If dictionary is empty after cleaning, check if we had text content
        if not result and '_text' in d:
            return d['_text']
        return result
    elif isinstance(d, list):
        return [clean_dict(item) for item in d]
    else:
        return d

def process_xml_to_yaml(xml_content, output_file=None):
    """Main function to process XML and convert to YAML
    
    Args:
        xml_content (str): XML content to process
        output_file (str, optional): Path to save the YAML output. If None, doesn't save to file.
        
    Returns:
        tuple: (fixed_xml, yaml_output)
    """
    # First, fix broken tags
    fixed_xml = fix_broken_tags(xml_content)
    
    # Wrap with root element if needed
    if not fixed_xml.strip().startswith('<?xml') and not re.match(r'^\s*<\w+', fixed_xml):
        fixed_xml = f"<root>{fixed_xml}</root>"
    
    # Check if XML is valid
    is_valid, error_msg = is_valid_xml(fixed_xml)
    if not is_valid:
        print(f"Warning: XML still has issues: {error_msg}")
        print("Attempting to continue with recovery mode...")
    
    # Convert to dictionary
    try:
        xml_dict = xml_to_dict(fixed_xml)
        # Clean the dictionary
        xml_dict = clean_dict(xml_dict)
        # Convert to YAML
        yaml_output = dict_to_yaml(xml_dict)
        
        # Save to file if output_file is provided
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(yaml_output)
            print(f"YAML output saved to {output_file}")
            
        return fixed_xml, yaml_output
    except Exception as e:
        return fixed_xml, f"Error during conversion: {str(e)}"

# Example usage
if __name__ == "__main__":
    # Define your XML content here
    xml_content = """
<prompt>
	<system instruction>
		You are a Verizon employee tasked with analyzing call transcripts to understand customer issues and generate c to identify new trends in calls, gauge customer experience through the sentiments captured in the calls along
	</system instruction›
	
	<Task Instruction>
		‹ul>
			‹li>For the given call transcript, extract the following information \li>
			‹li›*summary:* This should give the precise summary of the entire conversation without missing any details
			•.. So on
			‹li>
				tion answers pairs from the conversation provided. Make sure the questions are from the customer and the Make sure the question-answer pairs are limited to customer pain point. Don't include general conversatio
				example corresponding to the task(if Present):
				‹Example>
					‹Example1>
					‹transcript> </transcript>
					<output> </output>
					‹/Example1>
					‹Example2>
					<transcript> </transcript>
					<output> </output>
					‹/Example2>
				</ Example>
\
			‹/li>
		</ul>
	</Task Instruction>
	‹intent taxonomy Instruction>
		< Example>
		<transcript> </transcript>
		‹output>
		</ output>
		</Example>
	</intent taxonomy Instruction>
	<intent taxonomy list>
		txanomy1
		taxanomy2
		........
		taxanomy 3 
	</intent taxonomy list>
		‹Example>
			‹Example1>
			‹transcript> </transcript>
			<output> </output>
			‹/Example1>
			‹Example2>
			<transcript> </transcript>
			<output> </output>
			‹/Example2>
		</ Example>
</prompt>
    """
    
    fixed_xml, yaml_output = process_xml_to_yaml(xml_content)
    
    print("Fixed XML:")
    print(fixed_xml)
    print("\nYAML Output:")
    print(yaml_output)
