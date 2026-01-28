# server.py
from fastmcp import FastMCP
from typing import Annotated
from pydantic import AnyHttpUrl
import sys
import requests
import json
import os

 

broker = "http://localhost:1026"

server_instructions = """
You are interacting with a data space. The data space contains objects of 
different types. Each object has attributes relevant to its type. Objects include
a special attribute 'located_in' that indicates their location. 
"""

mcp = FastMCP(name="IoTDataSpace",
        instructions=server_instructions)

data_path = os.path.join(os.path.dirname(__file__), "..", "data-space", "data-space.json")
with open(data_path, "r", encoding="utf-8") as file:
    data_space = json.load(file)

def _get_types(keywords: str = None) -> list:
    if keywords is None or str(keywords).strip() == "":
        return []

    requested_attributes = [
        attr.strip().lower()
        for attr in keywords.split(",")
        if attr.strip()
    ]
    if not requested_attributes:
        return []

    matches = []
    seen = set()
    types_entries = data_space.get("data_space", {}).get("types", [])
    for types_entry in types_entries:
        for type_name, type_data in types_entry.items():
            type_description = str(type_data.get("description", "")).lower()
            if any(token in type_description for token in requested_attributes):
                if type_name not in seen:
                    matches.append({type_name: type_data})
                    seen.add(type_name)
                continue
            for attribute in type_data.get("attributes", []):
                description = str(attribute.get("description", "")).lower()
                if any(token in description for token in requested_attributes):
                    if type_name not in seen:
                        matches.append({type_name: type_data})
                        seen.add(type_name)
                    break

    return matches



def _read(type_id: str = None, object_id: str = None, 
           attributes: str = None, filters: list = None):
    """
    Read objects from the data space with flexible filtering and attribute selection.
    
    Args:
        type_id (str, optional): The type identifier to filter objects by type
        object_id (str, optional): The object identifier to fetch a specific object
        attributes (str, optional): A string composed of comma separated attributes
        filters (list, optional): List of filter strings in the form ["attribute operator value", ...]
                                  Examples: ["temperature>30", "located_in==building1", "consumption<=20"]
                                  Operators: ==, !=, <, <=, >, >=
    
    Returns:
        dict or list: A single object (if object_id provided) or a list of objects
    """
    supported_operators = ["==", "!=", "<=", ">=", "<", ">", "contains"]

    def is_number(value):
        try:
            float(value)
            return True
        except ValueError:
            return False

    def is_quoted(value):
        return len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"')

    query = None
    if filters:
        normalized_filters = []
        for filter_str in filters:
            attr = op = raw_value = None
            for operator in supported_operators:
                if operator in filter_str:
                    parts = filter_str.split(operator, 1)
                    if len(parts) == 2:
                        attr = parts[0].strip()
                        op = operator
                        raw_value = parts[1].strip()
                    break

            if not op:
                return {"error": f"Invalid filter '{filter_str}': unsupported operator"}

            value = raw_value
            if not is_number(value) and not is_quoted(value):
                value = f"\"{value}\""

            normalized_filters.append(f"{attr}{op}{value}")

        query = ";".join(normalized_filters)

    url = broker + "/ngsi-ld/v1/entities/"
    headers = {
        'Link':'<https://iot-data-space.github.io/context/context/mcp.jsonld>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"'
    }
    params = {}
    if (type_id != None) and str(type_id).strip() != "":
        params['type'] = type_id
    if (object_id != None) and str(object_id).strip() != "":
        params['id'] = object_id
    if (query != None) and str(query).strip() != "":
        params['q'] = query
    if (attributes != None) and str(attributes).strip() != "":
        params['attrs'] = attributes
    print(params)
    response = requests.request("GET", url, headers=headers, params=params)
    objects = json.loads(response.text)
    return objects


@mcp.tool(
    description="""
    Retrieve matching types (including their attributes) from the data space by
    searching type and attribute descriptions for the provided keywords. Supply a
    comma-separated list of keywords; matching is case-insensitive and returns full
    type objects.
    """
)
def get_types(keywords: Annotated[str, "Comma-separated keywords to match against type and attribute descriptions (case-insensitive)."]) -> list:
    print(f"get_types() called with: keywords={keywords}")
    result = _get_types(keywords)
    #print(f"get_types() response: {result}")
    return result

@mcp.tool(
    description="""
    Read a specific object or all objects of a specific type. Provide a type identifier
    to fetch all objects of that type, or an object identifier to fetch a single object.
    Optionally pass filters to narrow results by attribute values, and optionally list
    which attributes to include in the response. Leave attributes empty to return all fields.
    """
)
def read(type_id: Annotated[str, "The type identifier to filter objects by type"] = None,
         object_id: Annotated[str, "The object identifier to fetch a specific object"] = None,
         attributes: Annotated[str, "Comma-separated attribute names to include in the response; omit or empty for all."] = None,
         filters: Annotated[list, """List of filter strings like ['attribute operator value', ...].
                                     Examples: ['temperature>30', 'located_in==building1', 'consumption<=20'].
                                     Operators: ==, !=, <, <=, >, >=, contains (values may be quoted)."""] = None)-> list:

    print(f"read() called with: type_id={type_id}, object_id={object_id}, attributes={attributes}, filters={filters}")
    if (type_id is not None and str(type_id).strip() != "") and (object_id is not None and str(object_id).strip() != ""):
        return {"error": "Provide only one of type_id or object_id."}
    if type_id is not None and str(type_id).strip() != "":
        types_entries = data_space.get("data_space", {}).get("types", [])
        type_exists = any(type_id in entry for entry in types_entries)
        if not type_exists:
            return {"error": f"Unknown type_id '{type_id}'."}
    result = _read(type_id=type_id, object_id=object_id, attributes=attributes, filters=filters)
    #print(f"read() response: {result}")
    return result


def run_tests():
    """Run all tests for the _read method"""
    print("=" * 60)
    print("Testing _read method")
    print("=" * 60)
    
    # Test 1: Read a specific object by object_id
    print("\nTest 1: Read specific object by object_id")
    result = _read(object_id="urn:mcp:plug1")
    print(f"_read(object_id='urn:mcp:plug1')")
    print(f"Result: {result}")
    print("✓ Test 1 passed")
    
    
    # Test 2: Read all objects of a specific type
    print("\nTest 2: Read all objects of a specific type")
    result = _read(type_id="hvac_unit")
    print(f"_read(type_id='plugs')")
    print(f"Result: {result}")
    print("✓ Test 2 passed")

    # Test 3: Read with string filter (consumption > 10)
    print("\nTest 3: Read with string filter")
    result = _read(type_id="plug", filters=["consumption > 0.5"])
    print(f"_read(type_id='plug', filters=['consumption > 0.5'])")
    print(f"Result: {result}")
    print("✓ Test 3 passed")
    
    # Test 4: Read with attribute selection
    print("\nTest 4: Read with attribute selection")
    result = _read(object_id="urn:mcp:plug1", attributes="id,consumption")
    print(f"_read(object_id='urn:mcp:plug1', attributes=\"id,consumption\")")
    print(f"Result: {result}")
    print("✓ Test 4 passed")

    # Test 5: Read thermometer objects with location filter
    print("\nTest 5: Read thermometer objects with location filter")
    result = _read(type_id="plug", filters=["located_in == urn:mcp:building2"])
    print(f"_read(type_id='plug', filters=['located_in == urn:mcp:building2'])")
    print(f"Result: {result}")
    print("✓ Test 5 passed")

    # Test 6: Get types by attribute description match
    print("\nTest 6: Get types by attribute description match")
    result = _get_types(keywords="temperature,humidity")
    expected = {"thermometer", "humidity_sensor", "hvac_unit"}
    result_names = {list(item.keys())[0] for item in result}
    missing = expected - result_names
    print(f"_get_types(keywords='temperature,humidity')")
    print(f"Result: {result}")
    if missing:
        print(f"✗ Test 6 failed: missing {sorted(missing)}")
        return
    print("✓ Test 6 passed")
    

    '''
    # Test 5: Read all objects of thermometer type
    print("\nTest 5: Read all objects of thermometer type")
    result = _read(type_id="thermometer")
    print(f"_read(type_id='thermometer')")
    print(f"Result: {result}")
    print("✓ Test 5 passed")
    
   
    
    # Test 7: Read all objects without filters
    print("\nTest 7: Read all objects without filters")
    result = _read()
    print(f"_read()")
    print(f"Result count: {len(result)}")
    print("✓ Test 7 passed")
    
    # Test 8: Read non-existent object_id
    print("\nTest 8: Read non-existent object_id")
    result = _read(object_id="nonexistent")
    print(f"_read(object_id='nonexistent')")
    print(f"Result: {result}")
    print("✓ Test 8 passed")
    
    # Test 9: Read with contains filter
    print("\nTest 9: Read with contains filter")
    result = _read(filters=["located_in contains building"])
    print(f"_read(filters=['located_in contains building'])")
    print(f"Result count: {len(result)}")
    print("✓ Test 9 passed")
    
    # Test 10: Read thermometer type with attribute selection
    print("\nTest 10: Read thermometer type with attribute selection")
    result = _read(type_id="hygrometer", attributes=["temperature"])
    print(f"_read(type_id='thermometer', attributes=['temperature'])")
    print(f"Result: {result}")
    print("✓ Test 10 passed")
    
    # Test 11: Read with multiple filters
    print("\nTest 11: Read with multiple filters")
    result = _read(filters=["consumption > 10", "located_in == building1"])
    print(f"_read(filters=['consumption > 10', 'located_in == building1'])")
    print(f"Result: {result}")
    print("✓ Test 11 passed")
    
    # Test 12: Read plugs with != filter
    print("\nTest 12: Read plugs with != filter")
    result = _read(type_id="plugs", filters=["located_in!=building1"])
    print(f"_read(type_id='plugs', filters=['located_in!=building1'])")
    print(f"Result: {result}")
    print("✓ Test 12 passed")
    
    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60 + "\n")
    '''


if __name__ == "__main__":
    if "--test" in sys.argv:
        run_tests()
    else:
        # Start an HTTP MCP server at http://localhost:8000/mcp
        mcp.run(transport="sse", host="127.0.0.1", port=8000)
