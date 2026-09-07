# Setup

The speech engine needs two things beyond `pip install -e .`:

```bash
brew install espeak-ng
python3 -m pip install en_core_web_sm \
  --find-links https://github.com/explosion/spacy-models/releases/expanded_assets/en_core_web_sm-3.8.0
```

Both are real requirements, not conveniences:

- **espeak-ng** does grapheme-to-phoneme for words outside the dictionary.
  `espeakng-loader` ships a path from its own build machine that does not exist
  on your disk, so `speak.py` redirects it to the Homebrew install.
- **en_core_web_sm** is spaCy's English model. Without it Kokoro's tokenizer
  shells out to `uv` mid-run and takes the process down with it.

Neither failure is obvious from the error message, which is why they are
written down here rather than discovered again.
