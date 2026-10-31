"""Explicit listening/call-control policy after the 31 October transcript incident."""
from copy import deepcopy
import json

# None and empty strings trigger Bolna's default English wait announcement.
# A nonempty language map with empty values explicitly selects silent output.
SILENT_TOOL_MESSAGE={'hi':'','en':''}


def silence_callback_announcements(config):
    api=config.get('api_tools') or {}
    raw=api.get('tools',[])
    definitions=json.loads(raw) if isinstance(raw,str) else raw
    params=api.get('tools_params') or {}
    for definition in definitions:
        function=definition.get('function',definition)
        name=function.get('name')
        callback=params.get(name)
        if isinstance(callback,dict) and '/bolna/tools/' in callback.get('url',''):
            function['pre_call_message']=dict(SILENT_TOOL_MESSAGE)
            callback['pre_call_message']=dict(SILENT_TOOL_MESSAGE)
    if 'tools' in api:
        api['tools']=json.dumps(definitions,ensure_ascii=False) if isinstance(raw,str) else definitions

ENDPOINTING_MS=2500
RESPONSE_DELAY_MS=2500
LISTENING_MARKER='## Listening and call-control correction (31 October 2026)'
RESOLUTION_MARKER='Resolution workflow extension (preserve existing voice, language and intake rules)'
LISTENING_PROMPT=LISTENING_MARKER+'''
- Listen to the accumulated story across ALL user turns, not just the latest speech-recognition fragment. A job title alone is an opening. Do not answer each fragment, repeat acknowledgements, or start a questionnaire over an unfinished sentence.
- Never use “aap apni baat poori kijiye”, “main sun rahi hoon”, “please complete your story” or a similar filler as a standalone turn. Earlier generic acknowledgement examples are superseded by this rule. Do not repeatedly request permission to listen; leave the floor to the worker during narration.
- IMPORTANT TRANSITION: once the worker has described the work AND a wage/payment problem, the initial account is sufficient to proceed. You do not need the worker to say “finished”, speak a polished final sentence, or supply every wage figure. A trailing filler in the last recognition fragment does not erase the complete issue already described.
- At that transition, call capture_worker_account with ALL known facts before speaking. Unknown quantities remain null. Explicit “no money received” is payments_received=0. Then ask ONLY its returned next_question, in the active language, and wait for the answer. Do not prepend a request to finish the story. Once it returns next_action=calculate_reported_balance, use that tool; do not continue waiting or repeating intake questions.
- Example accumulated account: a construction worker in Hyderabad worked for a month, was promised Rs 1000 EACH WEEK, and has received no money. Capture workplace_location=Hyderabad, pay_basis=weekly, rate_per_unit=1000, payments_received=0, units_worked=null. A month is not automatically four weeks. The next spoken question is “आपने कुल कितने हफ़्ते का काम पूरा किया?” It is NOT “Ji, aap apni baat poori kijiye.”
- If the next answer is “चार हफ़्ते”, update units_worked=4 and retain weekly rate 1000 and receipts 0. Do not re-ask the rate, received money, name or city. Calculate through the backend after clarifying any genuine remaining ambiguity. Read back the result once and offer the next action.
- A mid-story “hello” normally checks whether you can hear them. Briefly acknowledge in the current active language and return the floor. It is not a request to switch to English or restart intake.
- If only fragments have reached you, say plainly that the full account has not reached you and invite them to continue. Do not imply the worker never explained it, invent the missing issue, or fill the gap with an intake questionnaire.
- When interrupted or asked to wait, stop the current question or explanation and let the worker continue. Retain the facts already given; do not ask the whole account again after a correction.
- Keep the selected active response language unless the worker explicitly requests another. Hindi/Hinglish and English speech must both be understood even if a few words use the other language.
- SPOKEN LANGUAGE OVERRIDE: when the active language is Hindi, write every spoken response in natural Hindi using Devanagari script. Do not produce Romanized Hindi. Use रुपये, हफ़्ते, हिसाब, परदे पर and सहेजना rather than rupees, per week, figures, screen, check or save. Preserve proper names and exact backend figures. An English word from the worker does not change the response language.
- The language switch system supplies its own acknowledgement. Do not also announce that you will speak Hindi or English. Continue with the next useful question in the requested language; do not repeat the previous answer or restart the account.
- Speak at most two short sentences per turn and ask at most ONE question. Do not combine a recap with several questions. After a correction, acknowledge only the changed fact if needed and move to the one missing fact; never repeat the entire story. Use the worker's name sparingly, not “Ji [name] ji” at every turn. Do not repeat a phrase, acknowledgement or number within the same reply. Tool calls are silent: do not add a waiting sentence before or between them. A single final read-back may be longer when required for informed confirmation.
- Do not finish or disconnect because of a completed read-back, a yes/no answer, saving, silence, or elapsed time. No automatic end-of-test script is appropriate. The worker controls ending through End conversation. Never say the worker ended a call unless that is actually known.
- SECTION MODE HAS PRIORITY over all general intake, story-collection and resolution rules above or below. Internal section instructions for this call: {section_guidance}
- When those internal instructions say SCOPED SECTION MODE, ask only the next question returned by guide_case_section. Never collect a story, ask another block's questions or call other case tools. Keep the call's initial Hindi/English language. The greeting has already asked the first question; process its answer without repeating it. All fields remain an unsaved browser draft. After completion, ask the worker to use this block's on-screen check/save buttons. Do not fill private final approval or submit a form. When section instructions say OFF, use the ordinary conversation rules.
'''


def inject_listening_prompt(text):
    """Own only this marked block, preserving base instructions/call variables."""
    if LISTENING_MARKER in text:
        start=text.index(LISTENING_MARKER)
        end=text.find(RESOLUTION_MARKER,start)
        text=text[:start]+(text[end:] if end>=0 else '')
    position=text.find(RESOLUTION_MARKER)
    if position>=0:return text[:position].rstrip()+'\n\n'+LISTENING_PROMPT.strip()+'\n\n'+text[position:]
    return text.rstrip()+'\n\n'+LISTENING_PROMPT.strip()+'\n'


def listening_configuration(agent):
    result=deepcopy(agent)
    result['agent_welcome_message']='{haqrecord_opening}'
    for task in result['tasks']:
        task['task_config'].update(incremental_delay=RESPONSE_DELAY_MS,number_of_words_for_interruption=1,
            optimize_latency=False,hangup_after_LLMCall=False,call_cancellation_prompt=None,
            hangup_after_silence=0,call_terminate=0,call_hangup_message=None)
        config=task['tools_config']
        silence_callback_announcements(config)
        config['transcriber'].update(provider='sarvam',model='saaras:v4',language='hi',stream=True,endpointing=ENDPOINTING_MS)
        multi=config.get('multilingual_config') or {}
        multi['language_switch_trigger']='caller_requested'
        for language,profile in multi.get('languages',{}).items():
            if language in ('hi','en'):
                profile.setdefault('transcriber',{}).update(provider='sarvam',model='saaras:v4',language=language,stream=True,endpointing=ENDPOINTING_MS)
            if language=='hi':profile['handoff_message']='जी, अब हिंदी में बात करेंगे।'
            if profile.get('system_prompt'):profile['system_prompt']=inject_listening_prompt(profile['system_prompt'])
        config['multilingual_config']=multi
    for profile in result.get('agent_prompts',{}).values():
        if isinstance(profile,dict) and profile.get('system_prompt'):profile['system_prompt']=inject_listening_prompt(profile['system_prompt'])
    for components in (result.get('composition_by_language') or {}).values():
        target=next((part for part in components if part.get('type')=='text' and (RESOLUTION_MARKER in part.get('text','') or LISTENING_MARKER in part.get('text',''))),None)
        if target is not None:target['text']=inject_listening_prompt(target['text'])
        else:components.append({'type':'text','text':'\n\n'+LISTENING_PROMPT})
        if not any(p.get('type')=='variable' and p.get('name')=='section_guidance' for p in components):
            components.extend([{'type':'text','text':'\nInternal section instructions (priority over general intake): '},
                {'type':'variable','scope':'execution','name':'section_guidance'}])
    return result
