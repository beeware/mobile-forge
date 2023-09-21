import re


def test_basic():
    import asyncio

    import aiohttp

    async def main():
        async with aiohttp.ClientSession() as session:
            async with session.get("http://python.org") as response:
                assert response.status == 200
                assert re.match(r"^text/html", response.headers["content-type"])

    asyncio.run(main())


# Check that the native module is being used.
def test_extension():
    from aiohttp import _http_parser, http_parser

    assert http_parser.HttpResponseParser is _http_parser.HttpResponseParser
    assert http_parser.HttpResponseParser is not http_parser.HttpResponseParserPy
