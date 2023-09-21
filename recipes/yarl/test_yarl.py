def test_basic():
    from yarl import URL

    assert (
        str(URL("http://εμπορικόσήμα.eu/путь/這裡"))
        == "http://xn--jxagkqfkduily1i.eu/%D0%BF%D1%83%D1%82%D1%8C/%E9%80%99%E8%A3%A1"
    )
