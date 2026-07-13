
import json

def json_to_text_tree(data, prefix=""):
    """Recursively generates a text tree representation of JSON/dict data."""
    if isinstance(data, dict):
        items = list(data.items())
        for i, (key, value) in enumerate(items):
            is_last = (i == len(items) - 1)
            connector = "└── " if is_last else "├── "
            
            if isinstance(value, (dict, list)):
                yield f"{prefix}{connector}{key}"
                next_prefix = prefix + ("    " if is_last else "│   ")
                yield from json_to_text_tree(value, next_prefix)
            else:
                yield f"{prefix}{connector}{key}: {value}"
                
    elif isinstance(data, list):
        for i, item in enumerate(data):
            is_last = (i == len(data) - 1)
            connector = "└── " if is_last else "├── "
            
            if isinstance(item, (dict, list)):
                yield f"{prefix}{connector}[Index {i}]"
                next_prefix = prefix + ("    " if is_last else "│   ")
                yield from json_to_text_tree(item, next_prefix)
            else:
                yield f"{prefix}{connector}{item}"


if __name__ == '__main__':
    # Example Usage:
    raw_json = """
    {
        "project": "AI Assistant",
        "version": "2.0",
        "settings": {
            "theme": "dark",
            "plugins": ["auth", "logger"]
        }
    }
    """

    data_dict = json.loads(raw_json)
    print("root")
    for line in json_to_text_tree(data_dict):
        print(line)
