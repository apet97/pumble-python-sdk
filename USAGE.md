<!-- Start SDK Example Usage [usage] -->
```python
# Synchronous Example
from pumble_keys import PumbleSDK


with PumbleSDK(
    api_key_auth="<YOUR_API_KEY_HERE>",
) as pumble_sdk:

    res = pumble_sdk.channels.list_channels()

    # Handle response
    print(res)
```

</br>

The same SDK client can also be used to make asynchronous requests by importing asyncio.

```python
# Asynchronous Example
import asyncio
from pumble_keys import PumbleSDK

async def main():

    async with PumbleSDK(
        api_key_auth="<YOUR_API_KEY_HERE>",
    ) as pumble_sdk:

        res = await pumble_sdk.channels.list_channels_async()

        # Handle response
        print(res)

asyncio.run(main())
```
<!-- End SDK Example Usage [usage] -->