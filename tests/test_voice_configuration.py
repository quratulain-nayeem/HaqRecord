import os
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import voice

with patch.dict(os.environ,{'BOLNA_API_KEY':'','BOLNA_AGENT_ID':''}):
    with patch('voice.dotenv_values',return_value={'BOLNA_API_KEY':' file-test-key ','BOLNA_AGENT_ID':' file-test-agent '}):
        assert voice.settings()=={'BOLNA_API_KEY':'file-test-key','BOLNA_AGENT_ID':'file-test-agent'}
with patch.dict(os.environ,{'BOLNA_API_KEY':'environment-test-key','BOLNA_AGENT_ID':'environment-test-agent'}):
    with patch('voice.dotenv_values',return_value={}):
        assert voice.settings()=={'BOLNA_API_KEY':'environment-test-key','BOLNA_AGENT_ID':'environment-test-agent'}
print('PASS: new .env keys override cached blanks; environment-only configuration still works.')
