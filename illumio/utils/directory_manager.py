# illumio/utils/directory_manager.py
"""
Utilities for managing application directories.
"""
import os

def get_app_root_dir():
    """
    Get the application root directory.
    
    Returns:
        str: Path to the application root directory
    """
    # Start with the current file's directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Navigate up to the root directory (2 levels up from illumio/utils)
    # illumio/utils -> illumio -> [app_root]
    app_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
    
    return app_root

def get_input_dir():
    """
    Get the input files directory.
    
    Returns:
        str: Path to the input files directory
    """
    app_root = get_app_root_dir()
    input_dir = os.path.join(app_root, 'input_files')
    
    # Create directory if it doesn't exist
    os.makedirs(input_dir, exist_ok=True)
    
    return input_dir

def get_output_dir():
    """
    Get the output files directory.
    
    Returns:
        str: Path to the output files directory
    """
    app_root = get_app_root_dir()
    output_dir = os.path.join(app_root, 'outputs')
    
    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    return output_dir

def get_file_path(filename, directory_type='output'):
    """
    Get the full path for a file in the input or output directory.
    
    Args:
        filename (str): Name of the file
        directory_type (str): 'input' or 'output'
    
    Returns:
        str: Full path to the file
    """
    if directory_type.lower() == 'input':
        directory = get_input_dir()
    else:
        directory = get_output_dir()
    
    return os.path.join(directory, filename)

def list_files(directory_type='input', extension=None):
    """
    List files in the input or output directory.
    
    Args:
        directory_type (str): 'input' or 'output'
        extension (str, optional): Filter by file extension
    
    Returns:
        list: List of filenames
    """
    if directory_type.lower() == 'input':
        directory = get_input_dir()
    else:
        directory = get_output_dir()
    
    if not os.path.exists(directory):
        return []
    
    if extension:
        if not extension.startswith('.'):
            extension = f".{extension}"
        return [f for f in os.listdir(directory) if f.endswith(extension)]
    else:
        return [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]