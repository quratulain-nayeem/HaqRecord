"""Worker-facing next actions; spoken answers intentionally contain no URLs."""
from decimal import Decimal


CONTACTS = {
    'hyderabad': {
        'name': 'Telangana Labour Department',
        'name_hi': 'तेलंगाना श्रम विभाग',
        'url': 'https://www.telangana.gov.in/departments/labour-employment-training-and-factories/',
        'phone': '040-27611437',
        'address': 'Commissioner of Labour, TAKS Bhavan, behind Devi Theatre, RTC X Road, Hyderabad',
        'checked_on': '2026-10-26',
    },
    'bengaluru': {
        'name': 'Karnataka State Legal Services Authority',
        'name_hi': 'कर्नाटक राज्य विधिक सेवा प्राधिकरण',
        'url': 'https://karnataka.nalsa.gov.in/contact-us/',
        'phone': '080-22111730',
        'address': '1st Floor, Nyaya Degula Building, H. Siddaiah Road, Bengaluru 560027',
        'checked_on': '2026-10-26',
    },
}


def resource_action_card(city, language='hi'):
    contact = CONTACTS[city]
    hi = language == 'hi'
    name = contact['name_hi'] if hi else contact['name']
    return {
        **contact, 'display_name': name, 'city': city,
        'title': 'मदद के लिए अगला कदम' if hi else 'A practical next step',
        'action': (f'{name} के प्रकाशित संपर्क से पहले पूछें कि आपके काम की जगह और मज़दूरी के मामले के लिए कौन-सा कार्यालय सही है।'
                   if hi else f'Use the published contact for {name} to ask which office handles the location and type of work in your account.'),
        'what_to_say': ('“मेरे काम की तय मज़दूरी पूरी नहीं मिली है। मेरे पास काम और मिले पैसों का सार है। कृपया सही कार्यालय, प्रक्रिया और आवश्यक दस्तावेज़ बताएं।”'
                        if hi else '“I have not received all the wages agreed for my work. I have a summary of the work and payments. Please tell me the appropriate office, process and required documents.”'),
        'bring': (['काम और मिले पैसों का जांचा हुआ सार', 'अगर उपलब्ध हों: भुगतान के रिकॉर्ड, संदेश और हाज़िरी', 'अनिश्चित भुगतान और विवादित बातों की अलग सूची']
                  if hi else ['Your reviewed account of work and payments', 'Payment records, messages and attendance, if available', 'A separate list of unclear payments and disputed facts']),
        'notice': ('यह प्रकाशित सामान्य संपर्क है। जाने से पहले सही कार्यालय और दस्तावेज़ों की पुष्टि करें। दस्तावेज़ न होने पर भी अपना खाता सुरक्षित रख सकते हैं। इससे शिकायत दर्ज नहीं हुई है।'
                    if hi else 'This is a published general contact. Confirm the appropriate office and requirements before visiting. Missing documents do not prevent saving your account. No complaint has been submitted.'),
        'spoken_response': (f'{name} की जानकारी स्क्रीन पर है। लिंक खोल सकते हैं; संपर्क करने से पहले सही कार्यालय पूछें। क्या मैं मदद मांगने के लिए आपकी बात का छोटा सार पढ़ दूँ?'
                            if hi else f'Information for {name} is on your screen. Use its contact to confirm the appropriate office. Would you like me to read a short summary you can use to ask for help?'),
        'jurisdiction_verified': False, 'complaint_submitted': False,
    }


def case_next_step(record, language='hi'):
    hi = language == 'hi'
    intake, calculation, workspace = record['intake'], record['calculation'], record.get('workspace', {})
    city = workspace.get('pilot_city')
    summary = (f"मेरी बताई जानकारी के अनुसार मैंने {calculation['units_worked']} {({'hourly':'घंटे','daily':'दिन','weekly':'हफ़्ते','monthly':'महीने','piece':'इकाई'}[calculation['pay_basis']])} काम किया। "
               f"हर {({'hourly':'घंटे','daily':'दिन','weekly':'हफ़्ते','monthly':'महीने','piece':'इकाई'}[calculation['pay_basis']])} ₹{calculation['rate_per_unit']} तय थे। "
               f"कुल कमाई ₹{calculation['total_earned']}, इस काम के मिले पैसे ₹{calculation['payments_received']}, और बाकी ₹{calculation['balance']} हैं।"
               if hi else f"Based on my reported account, I worked {calculation['units_worked']} {({'hourly':'hours','daily':'days','weekly':'weeks','monthly':'months','piece':'pieces'}[calculation['pay_basis']])} at INR {calculation['rate_per_unit']} per {({'hourly':'hour','daily':'day','weekly':'week','monthly':'month','piece':'piece'}[calculation['pay_basis']])}. "
               f"Reported earnings are INR {calculation['total_earned']}, wages received INR {calculation['payments_received']}, and the remaining amount INR {calculation['balance']}.")
    if calculation.get('provisional'):
        summary += (' यह अस्थायी हिसाब है; कुछ भुगतान या बातें अभी स्पष्ट करनी हैं।' if hi else ' This calculation is provisional; some payment allocations or facts remain unresolved.')
    if Decimal(calculation.get('promised_amount', '0')):
        summary += (' वादा किए गए पैसे मिले पैसों में नहीं जोड़े गए हैं।' if hi else ' Promised money has not been counted as received.')
    card = resource_action_card(city, language) if city in CONTACTS else None
    if calculation.get('provisional'):
        question = calculation.get('next_question_hi' if hi else 'next_question') or workspace.get('next_question_hi' if hi else 'next_question')
        spoken = ('कुछ रकम अभी स्पष्ट नहीं है। ' if hi else 'Some amounts still need clarification. ') + (question or '')
        kind = 'clarify'
    elif Decimal(calculation['balance']) < 0:
        question = 'क्या दर्ज सभी भुगतान इसी काम के थे?' if hi else 'Did all the recorded payments belong to this job?'
        spoken = ('दर्ज मिले पैसे बताई कमाई से अधिक हैं। ' if hi else 'Recorded receipts exceed the reported earnings. ') + question
        kind = 'review_balance';card=None
    elif Decimal(calculation['balance']) == 0:
        question = 'क्या कोई अलग अनसुलझी बात रिकॉर्ड में रखनी है?' if hi else 'Is there another unresolved issue you want to keep on record?'
        spoken = ('आपके बताए हिसाब में मज़दूरी का बाकी शून्य है। इससे कोई बाहरी शिकायत अपने आप वापस नहीं होती। ' if hi else 'Your reported wage balance is now zero. This does not automatically withdraw any external complaint. ') + question
        kind = 'balance_settled';card=None
    elif not card:
        question = 'काम कहाँ किया था: हैदराबाद या बेंगलुरु?' if hi else 'Where was the workplace: Hyderabad or Bengaluru?'
        spoken = ('आपका खाता तैयार है। सही सहायता की जानकारी के लिए ' if hi else 'Your account is ready. To identify relevant support, ') + question
        kind = 'confirm_city'
    else:
        question = ('क्या मैं मदद मांगने के लिए आपकी बात का छोटा सार पढ़ दूँ?' if hi else 'Would you like me to read a short summary you can use to ask for help?')
        spoken = card['spoken_response']
        kind = 'seek_support'
    return {'kind':kind,'title':'अब क्या कर सकते हैं?' if hi else 'What can you do next?',
            'summary':summary,'spoken_response':spoken,'next_question':question,'resource_card':card,
            'worker_name':intake.get('preferred_name',''),'original_statement':intake['original_statement'],
            'case_id':record.get('case_id'),'complaint_submitted':False,
            'follow_up':('अगर भुगतान का वादा हुआ है, उसे भुगतान न मानें। सहमत तारीख की वेबसाइट में याद रखें और पैसे मिलने पर इसी मामले को अपडेट करें।'
                         if hi else 'If payment was promised, keep it separate from received money. Set an agreed in-app reminder and update this same case when money arrives.')}


def voice_next_step(result, read_summary=False):
    """Only names and plain speech leave this boundary; links remain browser-side."""
    card = result.get('resource_card')
    return {'status':'next_step_ready','spoken_response':result['summary'] if read_summary else result['spoken_response'],
            'organisation':card['display_name'] if card else None,'contact_number_on_request':card['phone'] if card else None,
            'links_on_screen':bool(card),'complaint_submitted':False,
            'instruction':'Read spoken_response naturally. Do not read a URL or spell a website. Phone numbers are on screen; speak a number only if explicitly requested. Ask one question and wait.'}
