from app.services.podcast_generator import PodcastGenerator


def test_retry_delay_is_parsed_from_provider_message():
    error = Exception(
        "429 RESOURCE_EXHAUSTED. Please retry in 23.255769414s. "
        "{'details': [{'retryDelay': '19s'}]}"
    )

    delay_seconds = PodcastGenerator._parse_retry_delay_seconds(error)

    assert delay_seconds is not None
    assert round(delay_seconds, 3) == 23.256


def test_retry_delay_falls_back_to_retry_info_field():
    error = Exception("{'details': [{'retryDelay': '19s'}]}")

    delay_seconds = PodcastGenerator._parse_retry_delay_seconds(error)

    assert delay_seconds == 19.0


def test_long_script_is_trimmed_to_tts_quota_friendly_size():
    script = [{"speaker": "A" if index % 2 == 0 else "B", "text": f"line {index}"} for index in range(10)]

    trimmed = PodcastGenerator._trim_script(script)

    assert len(trimmed) == 8
    assert trimmed[:6] == script[:6]
    assert trimmed[-2:] == script[-2:]
