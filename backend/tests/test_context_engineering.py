import pytest
from app.rag.context_engineering import count_tokens

def test_tokenizer_dos_prevention():
    # Normal string
    assert count_tokens("hello world") > 0
    
    # Special tokens should not crash the tokenizer
    # Without the fix, enc.encode("<|endoftext|>") throws ValueError
    special_token = "<|endoftext|>"
    try:
        count = count_tokens(special_token)
        assert count > 0
    except ValueError:
        pytest.fail("Tokenizer crashed on special token (DoS vulnerability present).")
