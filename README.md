# Interact with IoT Data Space using LLMs

## Preparation

Install dependencies

```
python3 -m pip install fastmcp openai
```

The MCP server must be Internet accessible. Configure src/client.py with the URL of the MCP server.
Also you need an API access token from OpenAI.

## Execution

First run the data space following the instruction in the data space folder. Then run MCP server.
Finally, execute the client application using the instructions in the next section 

```
fastmcp run server.py --transport http --port 8000
```
## Use the client application


Fist execute 

```
export OPENAI_API_KEY="your_api_key_here"
```

```
python3 client.py
```


