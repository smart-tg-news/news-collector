from typing import Protocol, Dict, Any


class FieldProcessorException(Exception):
    pass


"""
Processor below defines the signature which any  
function or __call__ method for processing 
extra feed fields must follow
"""
class Processor(Protocol):
    def __call__(self, raw: Dict[str, Any], parsed: Dict[str, Any]) -> None:
        """
        Take `raw` (raw feed entry) and
        mutate `parsed` (the parsed dict) in-place.
        """
        ...


"""
Various processors implemeting the 
Processor signature
"""
def full_text_from_content(raw: Dict[str, Any], parsed: Dict[str, Any]) -> None:
    try:
        content_list = raw["content"]
    except KeyError:
        raise FieldProcessorException(
            'Field "content" not found in feed entry')
    
    # if multiple content items, pick the one with plain text
    entry_idx = 0
    for i, content_entry in enumerate(content_list):
        if (content_type := content_entry.get("type")) is not None:
            if content_type == "text_plain":
                entry_idx = i
                break
    content = content_list[entry_idx]
    
    # TODO: inside content entry language can also vary, 
    # filter entries with eng language if multiple options 
    # are present

    try:
        full_text = content["value"]
    except KeyError:
        raise FieldProcessorException(
            'Field "content.value" not found in feed entry')
    
    # key corresponds to NewsItem field
    parsed["full_text"] = full_text


def labels_from_tags(raw: Dict[str, Any], parsed: Dict[str, Any]) -> None:
    try:
        tags = raw["tags"]
    except KeyError:
        raise FieldProcessorException(
            'Field "tags" not found in feed entry')
    assert isinstance(tags, list)
    assert "term" in tags[0].keys()

    labels = [tag["term"] for tag in tags]

    # if some labels were already present
    if (prev_labels := parsed["meta"].get("labels")):
        if isinstance(prev_labels, list):
            parsed["meta"]["labels"].extend(labels)
        else:
            parsed["meta"]["labels"] = labels + [prev_labels]
    # if no labels were present
    else:
        parsed["meta"]["labels"] = labels


def set_explicit_label(raw: Dict[str, Any], parsed: Dict[str, Any], label: str) -> None:
    # if some labels were already present
    if (prev_labels := parsed["meta"].get("labels")):
        if isinstance(prev_labels, list):
            parsed["meta"]["labels"].append(label)
        else:
            parsed["meta"]["labels"] = [prev_labels, label]
    # if no labels were present
    else:
        parsed["meta"]["labels"] = [label]
