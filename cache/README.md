This cache holds files from the OpenAI Azure Blob Storage bucket
that the OpenAI `tiktoken` library requires.

In order to prevent the network request and relevant proxy updates to allow
traffic to Azure, we're caching a subset of the available files here.

The naming process is precise, as the `tiktoken` library looks for a specific
files in a configured cache directory (as specified in an environment variable).

See this: https://stackoverflow.com/a/76107077/4175042
