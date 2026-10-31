"""Export manual tool cards. Never sends requests to Bolna or changes its agent."""
import json
from pathlib import Path
from dotenv import dotenv_values


def inline_schema(schema):
    definitions=schema.get('$defs',{})
    def resolve(value):
        if isinstance(value,list):return [resolve(x) for x in value]
        if not isinstance(value,dict):return value
        if '$ref' in value:return resolve(definitions[value['$ref'].split('/')[-1]])
        return {k:resolve(v) for k,v in value.items() if k not in ('$defs','title','default')}
    return resolve(schema)


def conversation_schema(name, schema):
    if name not in ('calculate_reported_balance','prepare_case'):
        return schema
    # Browser compatibility aliases and full evidence reconstruction belong to
    # other APIs. Exposing them here let the model send conflicting wage fields.
    fields=['voice_token','pay_basis','units_worked','rate_per_unit','payments_received',
            'adjustments_clear','original_statement','preferred_name','workplace_location','employer_name','language']
    if name=='prepare_case':fields+=['consent_to_store','worker_confirmed']
    properties={key:schema['properties'][key] for key in fields}
    for key in ('rate_per_unit','payments_received'):
        properties[key]={'type':'string','description':'Confirmed rupees as digits, e.g. 3000.00. '+('Actually received, not promised.' if key=='payments_received' else 'Rate per agreed day, week or month.')}
    properties['units_worked']={'type':'integer','minimum':1,'maximum':10000,'description':'Completed days/weeks/months matching pay_basis exactly. Never convert monthly wages into weeks.'}
    for key in ('employer_name','workplace_location'):
        properties[key]={'type':'string','description':'Known value, or empty string if unknown. Optional personal detail; do not repeat questions or block calculation for this.'}
    properties['preferred_name']={'type':'string','description':'Known name; empty string for calculation if unknown, or Worker when preparing a case without a supplied name.'}
    properties['original_statement']={'type':'string','minLength':1,'description':'Latest worker account, including confirmed corrections. Preserve known facts; do not invent details.'}
    return {'type':'object','properties':properties,'required':fields,'additionalProperties':False}


def main():
    from voice_backend import ReconstructTool, FollowupTool, ReminderTool, PaymentTool, NextStepTool, CalculateTool, IntakeTool, AccountNotes
    root=Path(__file__).resolve().parent;public=dotenv_values(root/'.env').get('HAQRECORD_VOICE_PUBLIC_URL','').rstrip('/')
    output=root/'output'/'bolna-handoff';output.mkdir(parents=True,exist_ok=True)
    specs=[
        ('calculate_reported_balance','calculate',CalculateTool,
         'Calculate confirmed daily, weekly or monthly wages through the backend. Preserve the agreed unit exactly: five months at 2000 per month means monthly, 5, 2000. Never convert months to weeks. Count only money actually received for this case. Read only successful results; follow needs_clarification instructions.'),
        ('prepare_case','prepare-case',IntakeTool,
         'Prepare the confirmed case for private browser approval. Preserve daily, weekly or monthly wage basis exactly as agreed; never convert calendar months to weeks. Do not claim saving until browser approval succeeds.'),
        ('capture_worker_account','capture-account',AccountNotes,
         'Capture the account as the worker tells it, preserving daily, weekly or monthly rate units. Unknown facts remain null. Corrections replace outdated figures. Never infer weeks from calendar months.'),
        ('explain_case_next_step','next-step',NextStepTool,
         'When the worker asks what to do next, call this tool. It displays a practical action card and returns plain spoken text without URLs. Use read_summary=true only when the worker asks to hear the factual account for seeking assistance. Do not return to a save-instruction loop. Never read or spell URLs. This does not contact an office, file a complaint or guarantee jurisdiction.'),
        ('reconstruct_wage_dispute','reconstruct-dispute',ReconstructTool,
         'Reconstruct the initial wage account or propose a correction to the securely opened case. Use one stable payment_id per distinct payment. Preserve all prior payment entries and source references. Mark promises as promised. Received money of unknown job allocation stays unresolved. Only count received + this_case + worker_confirmed payments. Ask the returned next_question, not a fixed questionnaire. Existing-case corrections require worker confirmation and the current workspace version from read_current_case. All saving needs private browser approval.'),
        ('prepare_no_payment_followup','prepare-no-payment-followup',FollowupTool,
         'Prepare a confirmed follow-up saying no new money was received, optionally completing a pending in-app reminder. Use only this call\'s verified case. Ask browser approval; this does not save by itself.'),
        ('prepare_case_reminder','prepare-reminder',ReminderTool,
         'Prepare an in-app reminder only after the worker agrees to its action, date and time. due_at must include timezone, e.g. +05:30. It appears when the case is opened. No outbound telephone call, SMS or notification is scheduled. Private browser approval is required.'),
        ('prepare_payment','prepare-payment',PaymentTool,
         'Prepare confirmed additional money actually received for this securely opened case. Never record a promise or ambiguous job allocation as a payment. Pass a pending reminder_id from the current case if this payment completes that reminder. Browser approval and duplicate checks apply.'),
    ]
    for name,path,model,description in specs:
        schema=conversation_schema(name,inline_schema(model.model_json_schema()));properties=schema['properties']
        tool={'name':name,'description':description,'pre_call_message':{'en':'One moment while I check.','hi':'एक क्षण, जानकारी जाँच रही हूँ।'},
              'parameters':schema,'key':'custom_task','value':{'method':'POST','param':{k:{'$var':k} for k in properties},
              'url':public+'/bolna/tools/'+path,'api_token':'COPY_THE_EXISTING_BACKEND_BEARER_TOKEN_HERE',
              'headers':{'Content-Type':'application/json'},'pre_call_webhook_url':None,'pre_call_webhook_param':None}}
        (output/(name+'.json')).write_text(json.dumps(tool,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Exported manual tool cards to output/bolna-handoff. No requests made; credentials are placeholders.')


if __name__=='__main__':main()
