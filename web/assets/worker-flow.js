const $=id=>document.getElementById(id);
const words={
hi:{clarifyFigures:'आंकड़े या मज़दूरी का आधार स्पष्ट करना बाकी है। पुराने हिसाब को मंज़ूर न करें।',months:'महीने',monthsWorked:'कितने पूरे महीने काम किया?',monthlyRate:'हर महीने कितने रुपये तय हुए थे?',perMonth:'हर महीने के हिसाब से',skip:'मुख्य भाग पर जाएं',listen:'सुनकर समझें',demoNote:'अभी डेमो है। कृपया काल्पनिक जानकारी दें।',eyebrow:'आपका काम। आपका हक़।',heroTitle:'अपनी बात कहें।<br><span>हिसाब साफ़ करें।</span>',heroDescription:'मज़दूरी नहीं मिली? अपनी भाषा में बताएं। सारा आपकी बात सुनेगी और ज़रूरी सवाल एक-एक करके पूछेगी।',speak:'बोलकर बताएं',typeInstead:'या लिखकर बताएं',noLongForm:'लंबा फॉर्म भरने की ज़रूरत नहीं।',voiceCaption:'आप बोलें। सारा सुनेगी।',languages:'हिन्दी · English · Hinglish',newCase:'अपनी बात बताएं',newCaseHint:'नया मामला शुरू करें',existingCase:'मेरा मामला देखें',existingCaseHint:'मामला नंबर और पिन से खोलें',recordPayment:'नया भुगतान बताएं',recordPaymentHint:'मिले हुए पैसे जोड़ें',howTitle:'बस तीन आसान कदम',stepOne:'अपनी बात बताएं',stepOneHint:'बोलें, या अपनी सुविधा से लिखें।',stepTwo:'हिसाब देखें और सुनें',stepTwoHint:'कितना मिला, कितना बाकी है।',stepThree:'अपना मामला रखें',stepThreeHint:'जांचकर, निजी PIN से सुरक्षित करें।',backHome:'वापस जाएं',saraListens:'अपनी भाषा में बात करें',voiceTitle:'आराम से अपनी बात कहें।',voiceDescription:'जो याद है, उतना बताएं। बाकी सारा पूछ लेगी।',readySpeak:'बात शुरू करें',callReady:'बटन दबाएं और बोलें।',voiceConsent:'मैं AI सहायक से बात करने के लिए अपनी आवाज़ इस्तेमाल करने की अनुमति देता/देती हूँ।',startTalking:'बात शुरू करें',endCall:'बात खत्म करें',interruptHint:'आप बीच में रोक सकते हैं या भाषा बदलने को कह सकते हैं।',preferTyping:'बोलना मुश्किल है? लिखकर बताएं',privacyTitle:'आपकी आवाज़ और जानकारी',privacyDescription:'बातचीत के लिए Bolna और सुनने व बोलने के लिए Sarvam का इस्तेमाल होता है। रिकॉर्डिंग रखना सेवा की सेटिंग पर निर्भर है। अपना PIN, बैंक पासवर्ड या OTP कभी न बोलें।',weFillIt:'आप बोलें, जानकारी यहाँ आएगी।',weFillItHint:'सारा के सवालों के बाद आपका हिसाब यहाँ दिखेगा। पहले जांचें, फिर सुरक्षित करें।',yourAccount:'आपका बताया हुआ हिसाब',earned:'कुल कमाई',received:'मिले पैसे',remaining:'बाकी पैसे',hearAccount:'हिसाब सुनें',correctVoice:'कुछ गलत है? सारा को बताएं',accountNote:'यह आपके बताए आंकड़ों का हिसाब है, कानूनी फैसला नहीं।',choosePin:'अपना निजी पिन चुनें (6–12 अंक)',pinPrivate:'यहाँ लिखें। कॉल पर न बोलें।',saveConsent:'यह जानकारी सही है। मैं इसे सुरक्षित रखना चाहता/चाहती हूँ।',distinctPayment:'मैंने जांच लिया है। यह पहले वाले से अलग, नया भुगतान है।',saveCase:'मेरा मामला सुरक्षित करें',savePayment:'भुगतान सुरक्षित करें',savedTitle:'आपकी जानकारी सुरक्षित हो गई।',keepReference:'मामला दोबारा खोलने के लिए यह नंबर और अपना पिन संभालकर रखें।',notFiled:'इससे सरकारी शिकायत दर्ज नहीं हुई है।',viewMyCase:'मेरा मामला देखें',openCaseTitle:'अपना मामला खोलें।',openCaseHint:'अपना मामला नंबर और निजी पिन लिखें।',caseReference:'मामला नंबर',yourPin:'आपका पिन',openCase:'मामला खोलें',sharedPhone:'एक ही फोन इस्तेमाल करने से किसी दूसरे का मामला नहीं खुलता।',preferredName:'आपको किस नाम से बुलाएं? (ज़रूरी नहीं)',yourStory:'क्या हुआ? अपनी भाषा में लिखें।',paymentBasis:'मज़दूरी कैसे तय हुई थी?',perDay:'हर दिन के हिसाब से',perWeek:'हर हफ़्ते के हिसाब से',daysWorked:'कितने दिन काम किया?',weeksWorked:'कितने हफ़्ते काम किया?',dailyRate:'हर दिन कितने रुपये तय हुए थे?',weeklyRate:'हर हफ़्ते कितने रुपये तय हुए थे?',alreadyReceived:'अब तक कुल कितने रुपये मिले? कुछ नहीं मिला तो 0 लिखें।',workLocation:'काम कहाँ किया? (पता न हो तो छोड़ दें)',employerName:'मालिक या ठेकेदार का नाम (पता न हो तो छोड़ दें)',unknownOkay:'सारी जानकारी याद होना ज़रूरी नहीं है।',previous:'पीछे',continue:'आगे बढ़ें',yourCase:'आपका मामला',signOutCase:'मामला बंद करें / साइन आउट',paymentByVoice:'नया भुगतान बोलकर बताएं',downloadReceipt:'मामला पर्ची डाउनलोड करें',originalStatement:'आपकी बताई बात',stillUnknown:'अभी क्या जानना बाकी है',paymentHistory:'मिले पैसों का रिकॉर्ड',footerPrivacy:'आपका मामला आपके मामला नंबर और निजी पिन से खुलता है।',staffLogin:'सहायक का लॉगिन',connecting:'सारा से बात जुड़ रही है…',ringing:'बस एक पल…',active:'सारा सुन रही है। अपनी बात कहें।',ended:'बात खत्म हुई। तैयार जानकारी अभी भी जांचकर सुरक्षित कर सकते हैं।',serviceUnavailable:'बात करने की सेवा अभी नहीं जुड़ पा रही। थोड़ी देर बाद फिर कोशिश करें।',networkError:'कनेक्शन नहीं जुड़ पाया। इंटरनेट जांचें और फिर कोशिश करें।',micDenied:'माइक्रोफ़ोन की अनुमति नहीं मिली। ब्राउज़र में अनुमति दें और फिर कोशिश करें।',startFirst:'पहले सारा से बात शुरू करें। सारा आपकी जानकारी यहाँ लाएगी।',reviewTitle:'एक बार जांच लें।',paymentTitle:'मिले हुए नए पैसे जांच लें।',name:'नाम',duration:'किया गया काम',rate:'तय मज़दूरी',location:'काम की जगह',employer:'मालिक / ठेकेदार',unknown:'अभी पता नहीं',days:'दिन',weeks:'हफ़्ते',paymentDate:'पैसे मिलने की तारीख',paymentMethod:'कैसे मिले',cash:'नकद',transfer:'ट्रांसफ़र',genericWorker:'मज़दूर',caseSaved:'मामला सुरक्षित हो गया।',paymentSaved:'नया भुगतान सुरक्षित हो गया।',wrongAccess:'मामला नंबर या PIN सही नहीं है। दोबारा जांचें।',tooMany:'बहुत बार कोशिश हुई है। थोड़ी देर बाद फिर कोशिश करें।',changedDraft:'जानकारी बदल गई है। नया हिसाब जांचकर फिर मंज़ूरी दें।',duplicate:'ऐसा भुगतान पहले से दर्ज है। जांचें कि यह वही पैसे हैं या अलग, नया भुगतान।',sessionEnded:'सुरक्षा के लिए मामला फिर से खोलें।',invalidPin:'कृपया 6 से 12 अंकों का PIN लिखें।',required:'यह जानकारी भरें।',invalidNumber:'सही रकम या संख्या लिखें।',checkedAdjustments:'एडवांस और कटौती की पुष्टि अभी बाकी है।',unknownEmployer:'मालिक या ठेकेदार की जानकारी अभी बाकी है।',unknownLocation:'काम की जगह की जानकारी अभी बाकी है।',unknownDates:'काम की तारीखें अभी बाकी हैं।',unknownReminders:'सुरक्षित समय पर याद दिलाने की पसंद अभी बाकी है।',noHistory:'अभी कोई नया भुगतान नहीं जोड़ा गया है।',initialPayment:'पहले मिले पैसे',initialBalance:'शुरुआती बाकी पैसे',newPayment:'नया भुगतान',textTitles:['अपनी बात लिखें।','कितना काम किया?','पैसों का हिसाब बताएं।','काम के बारे में थोड़ा और।','जांचकर सुरक्षित करें।'],guide:'यह हक़ रिकॉर्ड है। मज़दूरी नहीं मिली तो बोलकर बताएं वाले बटन को दबाएं। सारा आपकी बात सुनेगी और एक एक सवाल पूछेगी। पुराना मामला देखने के लिए मेरा मामला देखें दबाएं। नए पैसे मिले हों तो नया भुगतान बताएं दबाएं। हिन्दी और इंग्लिश दोनों में बात कर सकते हैं।',voiceGuide:'पहले आवाज़ इस्तेमाल करने की अनुमति दें। फिर बात शुरू करें दबाएं। सारा को अपनी परेशानी बताएं। वह एक एक सवाल पूछेगी। आपकी जानकारी स्क्रीन पर आएगी। हिसाब जांचें और अपना निजी पिन यहाँ लिखकर मामला सुरक्षित करें। पिन कॉल पर कभी न बोलें।',noAudio:'इस डिवाइस पर पढ़कर सुनाना उपलब्ध नहीं है। आप सारा से बात कर सकते हैं।',beforeLeave:'कॉल चल रही है। पहले बात खत्म करें दबाएं।',correctionHint:'सारा से कहें कि कौन सी बात गलत है। वह सुधारकर नया हिसाब दिखा सकती है।',paymentHelp:'सारा को बताएं कि इस मामले के लिए अब कितने नए पैसे मिले हैं।',step:'कदम',of:'में से'},
en:{clarifyFigures:'The figures or wage agreement need clarification. Do not approve the previous calculation.',months:'months',monthsWorked:'How many complete months did you work?',monthlyRate:'How many rupees were agreed per month?',perMonth:'Per month',skip:'Skip to content',listen:'Listen to help',demoNote:'Demo version. Please use fictional information.',eyebrow:'YOUR WORK. YOUR RIGHT.',heroTitle:'Tell your story.<br><span>Know what you’re owed.</span>',heroDescription:'Wages unpaid? Tell us in your own language. Sara will listen and ask one simple question at a time.',speak:'Tell us by voice',typeInstead:'or type instead',noLongForm:'You don’t have to fill in a long form.',voiceCaption:'You speak. Sara listens.',languages:'Hindi · English · Hinglish',newCase:'Tell us what happened',newCaseHint:'Start a new case',existingCase:'Check my case',existingCaseHint:'Open with your reference and PIN',recordPayment:'Record a payment',recordPaymentHint:'Add money you have received',howTitle:'Just three simple steps',stepOne:'Tell your story',stepOneHint:'Speak, or write if you prefer.',stepTwo:'Check and hear the figures',stepTwoHint:'What you earned, received and are still owed.',stepThree:'Keep your case',stepThreeHint:'Review it and protect it with a private PIN.',backHome:'Go back',saraListens:'SPEAK IN YOUR OWN LANGUAGE',voiceTitle:'Take your time. We’re listening.',voiceDescription:'Tell us what you remember. Sara will ask about the rest.',readySpeak:'Ready when you are',callReady:'Press the button and speak.',voiceConsent:'I allow my voice to be used for this conversation with the AI assistant.',startTalking:'Start talking',endCall:'End conversation',interruptHint:'You can interrupt Sara or ask her to change language.',preferTyping:'Prefer not to speak? Type instead',privacyTitle:'Your voice and information',privacyDescription:'Bolna runs the conversation and Sarvam handles speech recognition and Sara’s voice. Recording retention depends on the service settings. Never say a PIN, bank password or OTP.',weFillIt:'Speak. We’ll fill in the details.',weFillItHint:'After Sara’s questions, your figures will appear here. Check them before saving.',yourAccount:'BASED ON WHAT YOU TOLD US',earned:'Earned',received:'Received',remaining:'Still owed',hearAccount:'Hear the figures',correctVoice:'Something wrong? Tell Sara',accountNote:'These figures are based on your account, not a legal decision.',choosePin:'Choose a private PIN (6–12 digits)',pinPrivate:'Type it here. Never say it on the call.',saveConsent:'I have checked these details. They are correct and I agree to save this record.',distinctPayment:'I checked the existing entry. This is a separate, additional payment.',saveCase:'Save my case',savePayment:'Save the payment',savedTitle:'Your record has been saved.',keepReference:'Keep this reference and your PIN somewhere private so you can return.',notFiled:'This has not filed a government complaint.',viewMyCase:'See my case',openCaseTitle:'Open your case.',openCaseHint:'Enter your case reference and private PIN.',caseReference:'Case reference',yourPin:'Your PIN',openCase:'Open my case',sharedPhone:'Sharing a phone does not give access to someone else’s case.',preferredName:'What should we call you? (Optional)',yourStory:'What happened? Write in your own words.',paymentBasis:'How was payment agreed?',perDay:'Per day',perWeek:'Per week',daysWorked:'How many days did you work?',weeksWorked:'How many weeks did you work?',dailyRate:'How many rupees were agreed per day?',weeklyRate:'How many rupees were agreed per week?',alreadyReceived:'How much have you received in total? Enter 0 if nothing.',workLocation:'Where did you work? (Leave blank if unknown)',employerName:'Employer or contractor (Leave blank if unknown)',unknownOkay:'It is okay not to remember every detail.',previous:'Back',continue:'Continue',yourCase:'YOUR CASE',signOutCase:'Close case / sign out',paymentByVoice:'Tell Sara about a payment',downloadReceipt:'Download case receipt',originalStatement:'What you told us',stillUnknown:'Still to clarify',paymentHistory:'Payment history',footerPrivacy:'Your case needs your reference and private PIN.',staffLogin:'Caseworker login',connecting:'Connecting you to Sara…',ringing:'Just a moment…',active:'Sara is listening. Tell your story.',ended:'Conversation ended. You can still check and save a prepared record.',serviceUnavailable:'The voice service cannot connect right now. Please try again shortly.',networkError:'Could not connect. Check your internet connection and try again.',micDenied:'Microphone permission was not granted. Allow it in your browser and try again.',startFirst:'Start speaking with Sara first. She will put your details here.',reviewTitle:'Take a moment to check.',paymentTitle:'Check the new payment.',name:'Name',duration:'Work completed',rate:'Agreed rate',location:'Work location',employer:'Employer / contractor',unknown:'Not yet known',days:'days',weeks:'weeks',paymentDate:'Date received',paymentMethod:'Payment method',cash:'Cash',transfer:'Transfer',genericWorker:'Worker',caseSaved:'Your case has been saved.',paymentSaved:'The new payment has been saved.',wrongAccess:'The case reference or PIN is incorrect. Please check and try again.',tooMany:'There have been too many attempts. Please try again later.',changedDraft:'The details changed. Check the latest figures before approving.',duplicate:'A similar payment is already recorded. Check whether these are the same funds or a separate payment.',sessionEnded:'For your privacy, open your case again.',invalidPin:'Please enter a PIN with 6 to 12 digits.',required:'Please fill in this detail.',invalidNumber:'Please enter a valid amount or number.',checkedAdjustments:'Advances and deductions still need checking.',unknownEmployer:'Employer or contractor details are still needed.',unknownLocation:'The work location is still needed.',unknownDates:'The work dates are still needed.',unknownReminders:'Safe reminder preferences are still needed.',noHistory:'No additional payment has been recorded yet.',initialPayment:'Initially received',initialBalance:'Initial amount owed',newPayment:'New payment',textTitles:['Tell us what happened.','How much work did you do?','Let’s check the money.','A little more about the work.','Check and save.'],guide:'Welcome to HaqRecord. If your wages are unpaid, press Tell us by voice. Sara will listen and ask one question at a time. To return to an existing case, press Check my case. If you received more money, press Record a payment. You can speak Hindi or English.',voiceGuide:'First allow your voice to be used, then press Start talking. Tell Sara what happened. She will ask one question at a time. Your details will appear on screen. Check the figures and type a private PIN here to save the case. Never say your PIN on the call.',noAudio:'Read-aloud is not available on this device. You can still speak with Sara.',beforeLeave:'Your call is still active. Press End conversation first.',correctionHint:'Tell Sara which detail is wrong. She can prepare corrected figures for you to check.',paymentHelp:'Tell Sara how much additional money you received for this case.',step:'Step',of:'of'}
};
Object.assign(words.hi,{resourceTitle:'अगला कदम जानें',resourceIntro:'हैदराबाद या बेंगलुरु के आधिकारिक स्रोत देखें। सही कार्यालय और प्रक्रिया की पुष्टि अधिकारी से करें।',resourceCity:'काम कहां किया?',chooseCity:'शहर चुनें',resourceIssue:'किस बारे में मदद चाहिए?',unpaidWages:'मज़दूरी नहीं मिली',deductionIssue:'कटौती पर विवाद',unsafeIssue:'धमकी या असुरक्षित स्थिति',officialSources:'आधिकारिक स्रोत देखें',freshResearch:'नई जानकारी खोजें',researchPrivacy:'नई खोज में केवल चुना हुआ शहर और समस्या भेजी जाएगी। आपका नाम, फ़ोन या दस्तावेज़ नहीं भेजे जाएंगे।',researchLoading:'जानकारी खोज रही हूँ…',researchMissing:'नई खोज अभी तैयार नहीं है। नीचे उपलब्ध आधिकारिक स्रोत देख सकते हैं।',researchNone:'इस जगह के लिए स्रोत की पुष्टि अभी बाकी है। किसी कार्यालय या समय-सीमा का अनुमान नहीं लगाया गया है।',researchFound:'आधिकारिक स्रोत नीचे हैं। सही क्षेत्र और मौजूदा प्रक्रिया की पुष्टि करें। इससे शिकायत दर्ज नहीं हुई है।',researchUnavailable:'अभी नई जानकारी नहीं मिली। बाद में फिर कोशिश करें।',researchLimit:'आज की खोज सीमा पूरी हो गई है। उपलब्ध आधिकारिक स्रोत देखें।',researchDiscovered:'खोज की तारीख',researchChecked:'स्रोत देखा गया',selectCity:'कृपया पहले काम का शहर चुनें।'});
Object.assign(words.en,{resourceTitle:'Find your next step',resourceIntro:'Start with official sources for Hyderabad or Bengaluru. Confirm the correct authority and procedure before submitting.',resourceCity:'Where did you work?',chooseCity:'Choose a city',resourceIssue:'What do you need help with?',unpaidWages:'Unpaid wages',deductionIssue:'Disputed deduction',unsafeIssue:'Threats or unsafe situation',officialSources:'See official sources',freshResearch:'Search for current information',researchPrivacy:'A fresh search sends only the selected city and issue. Your name, phone and evidence are not sent.',researchLoading:'Looking for official information…',researchMissing:'Fresh research is not configured yet. Available official sources are shown below.',researchNone:'Sources for this location still need checking. No office or deadline has been guessed.',researchFound:'Official sources are below. Confirm jurisdiction and current requirements. No complaint has been submitted.',researchUnavailable:'Fresh information is unavailable right now. Please try later.',researchLimit:'Today’s research limit has been reached. Use the available official sources.',researchDiscovered:'Found on',researchChecked:'Source checked',selectCity:'Please choose the work city first.'});
let resourceResult=null;
function renderResources(data){resourceResult=data;const key={research_not_configured:'researchMissing',research_unavailable:'researchUnavailable',research_limit_reached:'researchLimit',lookup_required:'researchNone',no_supported_sources:'researchNone'}[data.status]||'researchFound';$('resource-status').textContent=t(key);$('resource-links').replaceChildren();const seen=new Set();for(const source of [...data.directory,...data.sources]){const urlKey=source.url.replace(/\/$/,'');if(seen.has(urlKey))continue;seen.add(urlKey);const item=document.createElement('li'),link=document.createElement('a');link.textContent=(source.title||'').replace(/[\s:·.-]/g,'')?source.title:new URL(source.url).hostname;link.href=source.url;link.target='_blank';link.rel='noopener noreferrer';const note=document.createElement('small');note.textContent=' · '+t(source.kind==='research_source'?'researchDiscovered':'researchChecked')+': '+source.checked_on;item.append(link,note);$('resource-links').append(item);}}
async function loadResources(fresh=false){const city=$('resource-city').value;if(!city){$('resource-status').textContent=t('selectCity');return;}const button=$('fresh-research');button.disabled=true;$('resource-status').textContent=t('researchLoading');try{renderResources(await api('/resources/lookup','POST',{city,issue:$('resource-issue').value,language,fresh_lookup:fresh}));}catch{$('resource-status').textContent=t('researchUnavailable');}finally{button.disabled=false;}}
let language=localStorage.getItem('haqrecord_language')==='en'?'en':'hi';
let currentScreen='home',workerSession=null,caseRecord=null,afterAccess='case',textStep=0,textCalculation=null,textOperation=null;
Object.assign(words.hi,{speechLanguageHint:'हिन्दी या Hinglish के लिए ऊपर हिन्दी चुनें। English के लिए English चुनें।',checkMicrophone:'माइक जांचें',microphoneLabel:'माइक्रोफ़ोन',defaultMicrophone:'डिफ़ॉल्ट माइक्रोफ़ोन',micCheckPrivacy:'यह जांच सिर्फ़ इस ब्राउज़र में होती है। आवाज़ रिकॉर्ड या अपलोड नहीं होती।',micSaySomething:'कुछ बोलें। आवाज़ आने पर नीचे की पट्टी हिलेगी।',micSoundDetected:'माइक्रोफ़ोन आवाज़ पकड़ रहा है।',micNoSound:'आवाज़ नहीं मिली। दूसरा माइक्रोफ़ोन चुनें और जांचें कि वह म्यूट नहीं है।',micConsent:'माइक जांचने के लिए पहले आवाज़ इस्तेमाल करने की अनुमति दें।'});
Object.assign(words.en,{speechLanguageHint:'Speaking Hindi or Hinglish? Choose हिन्दी above. Choose English if you will speak English.',checkMicrophone:'Check my microphone',microphoneLabel:'Microphone',defaultMicrophone:'Default microphone',micCheckPrivacy:'This check stays in your browser. Audio is not recorded or uploaded.',micSaySomething:'Say a few words. The bar should move when you speak.',micSoundDetected:'Your microphone is picking up sound.',micNoSound:'No sound detected. Try another microphone and check it is not muted.',micConsent:'Please allow voice use before checking your microphone.'});
Object.assign(words.hi,{voiceUnknownError:'वॉइस का यह कदम पूरा नहीं हुआ। कारण की अभी पुष्टि नहीं हुई है। इसे इंटरनेट की समस्या नहीं माना जा रहा।',micUnavailable:'चुना हुआ माइक्रोफ़ोन उपलब्ध नहीं है। माइक जांचें में दूसरा माइक्रोफ़ोन चुनें।',micBusy:'ब्राउज़र माइक्रोफ़ोन खोल नहीं पाया। जांचें कि कोई दूसरा ऐप उसे रोक तो नहीं रहा।',voiceProviderError:'वॉइस सेवा से कॉल शुरू नहीं हो पाई। इस प्रयास से मामला सुरक्षित नहीं हुआ।',voiceConnectFailed:'Bolna से वॉइस कॉल कनेक्ट नहीं हुई। यह संदेश इंटरनेट खराब होने का प्रमाण नहीं है। अभी लिखकर मामला बना सकते हैं।',audioPlaybackBlocked:'ब्राउज़र ने आवाज़ चलने से रोकी। आवाज़ की अनुमति देकर फिर बटन दबाएं।'});
Object.assign(words.en,{voiceUnknownError:'This voice step failed. The cause has not yet been identified; this is not being assumed to be an internet problem.',micUnavailable:'The selected microphone is unavailable. Choose another input under Check my microphone.',micBusy:'The browser could not open the microphone. Check whether another app is blocking it.',voiceProviderError:'The voice service could not start this call. No case was saved by this attempt.',voiceConnectFailed:'The voice call did not connect to Bolna. This does not establish an internet problem. Text intake is still available.',audioPlaybackBlocked:'The browser blocked voice playback. Allow audio and press the button again.'});
Object.assign(words.en,{voiceDisconnected:'The call connection ended unexpectedly. The cause is not confirmed. Any figures already on screen remain available for review. You can reconnect.'});
Object.assign(words.hi,{voiceDisconnected:'कॉल का संपर्क अचानक समाप्त हुआ। कारण की पुष्टि नहीं है। स्क्रीन पर आ चुका हिसाब अभी भी जांच सकते हैं। फिर से कॉल जोड़ सकते हैं।'});
Object.assign(words.en,{stopMicrophone:'Stop microphone check',micQuiet:'Listening for sound. Speak to see the bar move.',micStopped:'Microphone check stopped.',micStarting:'Opening your microphone…',micCheckPrivacy:'This bar checks local microphone sound, including during a call. It does not confirm that Sara received or transcribed your words. The check itself does not record or upload audio.'});
Object.assign(words.hi,{stopMicrophone:'माइक जांच बंद करें',micQuiet:'आवाज़ का इंतज़ार है। बोलने पर पट्टी हिलेगी।',micStopped:'माइक जांच बंद है।',micStarting:'माइक्रोफ़ोन खोल रहे हैं…',micCheckPrivacy:'यह पट्टी कॉल के दौरान भी इस ब्राउज़र में माइक की आवाज़ जांचती है। इससे यह पुष्टि नहीं होती कि सारा ने शब्द सुने या लिखे। जांच खुद आवाज़ रिकॉर्ड या अपलोड नहीं करती।'});
let selectedMicrophone='',micCheckStream=null,micCheckContext=null,micCheckFrame=null,micCheckActive=false,micCheckGeneration=0,micCheckOwnsStream=true;
function microphoneConstraints(){return {echoCancellation:true,noiseSuppression:true,autoGainControl:true,...(selectedMicrophone?{deviceId:{exact:selectedMicrophone}}:{})};}
function updateMicrophoneCheckControls(){
  $('check-microphone').disabled=false;
  $('check-microphone').textContent=t(micCheckActive?'stopMicrophone':'checkMicrophone');
  $('microphone-device').disabled=busy;
  $('microphone-level').hidden=!micCheckActive;
  if(!micCheckActive)$('microphone-check-status').textContent=t('micStopped');
}
async function stopMicrophoneCheck(){
  micCheckActive=false;micCheckGeneration++;
  if(micCheckFrame!==null)cancelAnimationFrame(micCheckFrame);micCheckFrame=null;
  const stream=micCheckStream,context=micCheckContext,owned=micCheckOwnsStream;micCheckStream=null;micCheckContext=null;micCheckOwnsStream=true;
  if(stream&&owned)stream.getTracks().forEach(track=>track.stop());
  $('microphone-level').value=0;$('microphone-check-status').textContent=t('micStopped');
  updateMicrophoneCheckControls();
  if(context)await context.close().catch(()=>{});
}
async function checkMicrophone(){
  if(micCheckActive){await stopMicrophoneCheck();return;}
  if(!$('voice-consent').checked){notify('voice-message',t('micConsent'));return;}
  notify('voice-message','');micCheckActive=true;const generation=++micCheckGeneration;
  $('mic-check-panel').hidden=false;$('microphone-level').value=0;
  $('microphone-check-status').textContent=t('micStarting');updateMicrophoneCheckControls();
  const cancelled=()=>generation!==micCheckGeneration||!$('voice-consent').checked;
  try{
    const tracks=callState==='active'?(window.HaqCallAudio?.audioTracks(call)||[]):[];
    const owned=!tracks.length;
    const stream=owned?await navigator.mediaDevices.getUserMedia({audio:microphoneConstraints(),video:false}):new MediaStream(tracks);
    if(cancelled()){if(owned)stream.getTracks().forEach(track=>track.stop());return;}
    micCheckStream=stream;micCheckOwnsStream=owned;
    const devices=await navigator.mediaDevices.enumerateDevices();
    if(cancelled())return;
    const select=$('microphone-device');select.replaceChildren();
    const def=document.createElement('option');def.value='';def.textContent=t('defaultMicrophone');select.append(def);
    for(const device of devices.filter(item=>item.kind==='audioinput')){const option=document.createElement('option');option.value=device.deviceId;option.textContent=device.label||t('microphoneLabel');select.append(option);}select.value=selectedMicrophone;
    const AudioContextType=window.AudioContext||window.webkitAudioContext;
    const context=new AudioContextType();micCheckContext=context;await context.resume();
    if(cancelled())return;
    const source=context.createMediaStreamSource(stream),analyser=context.createAnalyser();analyser.fftSize=1024;source.connect(analyser);
    const samples=new Float32Array(analyser.fftSize);
    const update=()=>{
      if(cancelled()||!micCheckActive)return;
      analyser.getFloatTimeDomainData(samples);
      let sum=0;for(const value of samples)sum+=value*value;
      const rms=Math.sqrt(sum/samples.length);
      // Logarithmic scaling makes quiet speech visible without pegging the bar.
      $('microphone-level').value=Math.max(0,Math.min(1,(20*Math.log10(Math.max(rms,.000001))+60)/48));
      const status=rms>.008?'micSoundDetected':'micQuiet';
      if($('microphone-check-status').textContent!==t(status))$('microphone-check-status').textContent=t(status);
      micCheckFrame=requestAnimationFrame(update);
    };update();
  }catch(error){if(generation!==micCheckGeneration)return;await stopMicrophoneCheck();$('microphone-check-status').textContent=humanError(error);}
}
Object.assign(words.hi,{notesTitle:'आपकी बात यहाँ आ रही है',notesUnconfirmed:'यह अधूरी जानकारी है। जांच और आपकी अनुमति के बाद ही मामला सुरक्षित होगा।'});
Object.assign(words.en,{notesTitle:'Here is what we have heard',notesUnconfirmed:'These details are incomplete and need checking. Nothing is saved until you review and approve.'});
let accountNotes=null;
function renderAccountNotes(notes){accountNotes=notes;$('empty-review').hidden=true;$('captured-notes').hidden=false;$('draft-review').hidden=true;$('voice-saved').hidden=true;$('captured-statement').textContent=notes.original_statement;$('captured-facts').replaceChildren();for(const [key,value] of [['name',notes.preferred_name],['location',notes.workplace_location],['employer',notes.employer_name],['duration',notes.units_worked?`${notes.units_worked} ${notes.pay_basis?t(({hourly:'hours',daily:'days',weekly:'weeks',monthly:'months',piece:'pieces'})[notes.pay_basis]):''}`:null],['rate',notes.rate_per_unit],['received',notes.payments_received]])if(value!==null&&value!==undefined&&value!=='')addFact($('captured-facts'),key,String(value));$('captured-questions').textContent=notes.next_question||notes.unresolved_questions||'';}
let calculationPreview=null,previewRevision='',voiceConfigurationStatus='',voiceConfigurationWarnings=[];
Object.assign(words.hi,{settingsChanged:'सारा की सेटिंग बदल गई हैं। सही सेटिंग वापस आने तक नई कॉल शुरू नहीं होगी। लिखकर मामला बना सकते हैं।'});
Object.assign(words.en,{settingsChanged:'Sara’s settings changed. Calls are paused until the tested settings are restored. You can still create your case by typing.'});
Object.assign(words.hi,{story:'आपके साथ क्या हुआ?',previewNote:'हिसाब तैयार है, मामला अभी सुरक्षित नहीं हुआ। जानकारी जांचें और नीचे PIN से सुरक्षित करें।'});
Object.assign(words.en,{story:'What happened?',previewNote:'Your figures are ready. The case is not saved yet. Check the details and save with a private PIN below.'});
let call=null,busy=false,voiceReady=false,voiceCsrf='',voiceMode='new',draft=null,lastDraftId='',savedVoiceResult=null,timer=null,polling=false,savingVoice=false,callState='ready';
const t=key=>words[language][key]||words.en[key]||key;
const money=value=>'₹'+Number(value).toLocaleString(language==='hi'?'en-IN':'en-IN',{maximumFractionDigits:2});
Object.assign(words.en,{newCase:'Tell us what happened',existingCase:'Continue my case',recordPayment:"Record today’s work",recordPaymentHint:'Keep your own work diary',earned:'Reported earnings',received:'Wages received',remaining:'Remaining wages',hourly:'Per hour',piece:'Per piece',hours:'hours',pieces:'pieces',hoursWorked:'How many confirmed hours?',piecesWorked:'How many confirmed pieces?',hourlyRate:'Agreed rupees per hour',pieceRate:'Agreed rupees per piece'});
Object.assign(words.hi,{newCase:'क्या हुआ, बताएं',existingCase:'मेरा मामला आगे बढ़ाएं',recordPayment:'आज का काम दर्ज करें',recordPaymentHint:'काम की अपनी डायरी रखें',earned:'बताई गई कमाई',received:'मिली मज़दूरी',remaining:'बाकी मज़दूरी',hourly:'हर घंटे के हिसाब से',piece:'हर इकाई के हिसाब से',hours:'घंटे',pieces:'इकाइयां',hoursWorked:'कितने घंटे पुष्ट हैं?',piecesWorked:'कितनी इकाइयां पुष्ट हैं?',hourlyRate:'हर घंटे के तय रुपये',pieceRate:'हर इकाई के तय रुपये'});
Object.assign(words.en,{caseDetails:'Your story and payments',listen:'Hear help',heroDescription:'Wages unpaid? Tell Sara what happened.',voiceDescription:'Speak at your own pace.',correctVoice:'Correct a detail',hearAccount:'Hear my figures',signOutCase:'Close my case',earned:'Earned',received:'Received',remaining:'Still owed',choosePin:'Choose a PIN (6–12 digits)',guide:'For unpaid wages, press Tell us by voice. To return, press Continue my case. To keep a work diary, press Record today’s work.',voiceGuide:'Allow voice use, then press Start talking. Tell Sara what happened. Check your figures before saving. Type your PIN privately. Never say it on the call.'});
Object.assign(words.hi,{caseDetails:'आपकी बात और मिले पैसे',listen:'मदद सुनें',heroDescription:'मज़दूरी नहीं मिली? सारा को अपनी बात बताएं।',voiceDescription:'आराम से अपनी बात कहें।',correctVoice:'जानकारी सुधारें',hearAccount:'हिसाब सुनें',signOutCase:'मामला बंद करें',earned:'कमाई',received:'मिले पैसे',remaining:'बाकी पैसे',choosePin:'PIN चुनें (6–12 अंक)',guide:'मज़दूरी नहीं मिली तो बोलकर बताएं दबाएं। पुराना मामला खोलने के लिए मेरा मामला आगे बढ़ाएं दबाएं। काम की डायरी के लिए आज का काम दर्ज करें दबाएं।',voiceGuide:'आवाज़ इस्तेमाल करने की अनुमति दें। फिर बात शुरू करें दबाएं और अपनी बात कहें। सहेजने से पहले हिसाब जांचें। PIN खुद लिखें, कॉल पर न बोलें।'});
function notify(id,text){$(id).textContent=text;$(id).hidden=!text;}
function setLanguage(next){
  window.HaqReadAloud?.stop();
  language=next;localStorage.setItem('haqrecord_language',next);document.documentElement.lang=next;
  document.querySelectorAll('[data-i18n]').forEach(node=>{const key=node.dataset.i18n;if(key==='heroTitle')node.innerHTML=t(key);else node.textContent=t(key);});
  $('lang-hi').setAttribute('aria-pressed',String(next==='hi'));$('lang-en').setAttribute('aria-pressed',String(next==='en'));
  $('hero-mic').setAttribute('aria-label',t('speak'));document.title=next==='hi'?'HaqRecord — अपनी बात कहें':'HaqRecord — Tell your story';document.querySelector('.header-actions').setAttribute('aria-label',next==='hi'?'भाषा और मदद':'Language and help');
  $('listen-guide').setAttribute('aria-label',t('listen'));$('listen-voice-help').setAttribute('aria-label',t('listen'));
  updateTextStep();updateCall();
  if(resourceResult)renderResources(resourceResult);
  if(draft&&!savedVoiceResult)renderDraft(draft,true);
  else if(calculationPreview&&!savedVoiceResult)renderCalculationPreview(calculationPreview,true);
  if(caseRecord)renderCase(caseRecord);
  if(savedVoiceResult)renderVoiceSaved(savedVoiceResult);
  else if(accountNotes&&!calculationPreview&&!draft)renderAccountNotes(accountNotes);
  window.dispatchEvent(new CustomEvent('haqrecord-language',{detail:next}));
  if(currentScreen==='voice'&&voiceCsrf)refreshVoice().catch(()=>{});
}
function showScreen(name){
  if(busy&&name!=='voice'){notify('voice-message',t('beforeLeave'));return;}
  if(name!=='voice'&&micCheckActive)stopMicrophoneCheck();
  currentScreen=name;
  for(const section of ['home','voice','access','text','case'])$(section+'-screen').hidden=section!==name;
  notify('page-message','');window.scrollTo({top:0,behavior:'smooth'});
}
function speak(text){
  if(busy){notify('voice-message',t('beforeLeave'));return;}
  if(!('speechSynthesis' in window)){notify('page-message',t('noAudio'));return;}
  if(window.HaqReadAloud){window.HaqReadAloud.read(text,language);return;}
  speechSynthesis.cancel();const utterance=new SpeechSynthesisUtterance(text);utterance.lang=language==='hi'?'hi-IN':'en-IN';utterance.rate=.9;
  const voices=speechSynthesis.getVoices();const matching=voices.find(voice=>voice.lang.toLowerCase().startsWith(language));if(matching)utterance.voice=matching;speechSynthesis.speak(utterance);
}
function humanError(error){
  // SDK events expose cause; rejected start() errors expose cause2. Preserve
  // the actual category in both paths without displaying provider credentials.
  const chain=[];let current=error;
  for(let n=0;current&&n<5;n++){chain.push(current);current=current.cause||current.cause2;}
  const hasCode=code=>chain.some(item=>item.code===code);
  const status=chain.find(item=>Number.isInteger(item.status))?.status;
  if(hasCode('voice_configuration_changed'))return t('settingsChanged');
  if(chain.some(item=>item.name==='NotFoundError'||item.name==='OverconstrainedError'))return t('micUnavailable');
  if(chain.some(item=>item.name==='NotReadableError'||item.name==='AbortError'))return t('micBusy');
  if(hasCode('microphone_denied')||chain.some(item=>item.name==='NotAllowedError'))return t('micDenied');
  if(hasCode('possible_duplicate'))return t('duplicate');
  if(status===429||hasCode('at_capacity'))return t('tooMany');
  if(status===401)return currentScreen==='access'?t('wrongAccess'):t('sessionEnded');
  if(status===409)return t('changedDraft');
  if(status===502||hasCode('mint_failed'))return t('voiceProviderError');
  if(status===503)return t('serviceUnavailable');
  if(hasCode('connect_failed')||hasCode('call_rejected'))return t('voiceConnectFailed');
  if(hasCode('autoplay_blocked'))return t('audioPlaybackBlocked');
  return t(currentScreen==='voice'?'voiceUnknownError':'networkError');
}

async function api(path,method='GET',body=null,csrf=null){
  const headers={};if(body!==null)headers['Content-Type']='application/json';if(csrf)headers['X-CSRF-Token']=csrf;
  const response=await fetch(path,{method,headers,...(body!==null?{body:JSON.stringify(body)}:{})});
  const data=await response.json();if(!response.ok){const error=new Error(typeof data.detail==='string'?data.detail:data.detail?.message||'Request failed');error.status=response.status;error.code=data.detail?.code;throw error;}return data;
}
function startVoice(mode='new'){
  if(busy){showScreen('voice');return;}
  if(mode==='existing'&&!workerSession){afterAccess='payment';showScreen('access');return;}
  voiceMode=mode;showScreen('voice');
  if(!busy){callState='ready';updateCall();}
  notify('voice-message',voiceReady?'':t(voiceConfigurationStatus==='configuration_changed'?'settingsChanged':'serviceUnavailable'));
  refreshVoiceAvailability().catch(()=>{});
}
let checkingVoiceAvailability=false;
async function refreshVoiceAvailability(){
  if(busy||checkingVoiceAvailability)return;
  checkingVoiceAvailability=true;
  const wasReady=voiceReady;
  const previousMessage=$('voice-message').textContent;
  const availabilityMessages=[t('serviceUnavailable'),t('settingsChanged')];
  try{
    const status=await api('/voice/status');
    voiceReady=Boolean(status.ready&&status.backend_connected);
    voiceConfigurationStatus=status.agent_configuration||'';
    voiceConfigurationWarnings=status.agent_warnings||[];
  }catch{voiceReady=false;}
  finally{checkingVoiceAvailability=false;}
  updateCall();
  // Only replace availability notices; preserve microphone and call errors.
  if(currentScreen==='voice'&&!busy&&$('voice-message').textContent===previousMessage&&(!previousMessage||availabilityMessages.includes(previousMessage))){
    if(!voiceReady)notify('voice-message',t(voiceConfigurationStatus==='configuration_changed'?'settingsChanged':'serviceUnavailable'));
    else if(!wasReady)notify('voice-message','');
  }
}
Object.assign(words.hi,{voiceSettingsAdvisory:'वॉइस कॉल सारा की मौजूदा सेटिंग के साथ उपलब्ध है।',voiceDetailsAdvisory:'वॉइस कॉल शुरू कर सकते हैं। इस सेटअप में जानकारी मज़दूरी का हिसाब होने के बाद दिखेगी।'});
Object.assign(words.en,{voiceSettingsAdvisory:'Voice calls are available with the current agent settings.',voiceDetailsAdvisory:'Voice calls are available. In this setup, details appear after the wage calculation.'});
function renderVoiceConfigurationNote(){
  const note=$('voice-configuration-note');note.hidden=!voiceReady||voiceConfigurationStatus!=='configuration_warning';
  note.textContent=note.hidden?'':t(voiceConfigurationWarnings.some(code=>code==='early_account_capture'||code==='preview_fields')?'voiceDetailsAdvisory':'voiceSettingsAdvisory');
}
function updateCall(){
  renderVoiceConfigurationNote();
  $('start-call').disabled=busy||!voiceReady||!$('voice-consent').checked;$('start-call').hidden=busy;$('stop-call').hidden=!busy;
  updateMicrophoneCheckControls();
  $('conversation-orb').classList.toggle('active',busy);$('voice-consent-label').hidden=busy;
  $('call-heading').textContent=t(callState==='active'?'active':callState==='ended'?'ended':'readySpeak');
  $('call-status').textContent=t({ready:'callReady',connecting:'connecting',ringing:'ringing',active:'interruptHint',ended:'ended'}[callState]||'callReady');
}
function addFact(list,key,value){const cell=document.createElement('div');const term=document.createElement('dt');const detail=document.createElement('dd');term.textContent=t(key);detail.textContent=value||t('unknown');cell.append(term,detail);list.append(cell);}
function renderDraft(state,force=false){
  if(!force&&lastDraftId===state.draft_id)return;
  $('captured-notes').hidden=true;
  $('preview-editor').hidden=true;
  const changed=lastDraftId!==state.draft_id;draft=state;lastDraftId=state.draft_id;savedVoiceResult=null;
  $('empty-review').hidden=true;$('draft-review').hidden=false;$('voice-saved').hidden=true;
  const intake=state.draft_kind!=='payment',newIntake=state.draft_kind==='intake';$('draft-heading').textContent=t(intake?'reviewTitle':'paymentTitle');
  $('voice-pin-wrap').hidden=!newIntake;$('voice-pin').required=newIntake;
  $('approve-voice-button').querySelector('span').textContent=t(intake?'saveCase':'savePayment');
  if(changed){$('approve-voice').checked=false;$('voice-pin').value='';$('distinct-payment').checked=false;$('distinct-wrap').hidden=true;notify('approval-message','');}
  $('draft-facts').replaceChildren();
  if(intake){const data=state.draft.intake,c=state.draft.calculation;$('draft-earned').textContent=money(c.total_earned);$('draft-received').textContent=money(c.payments_received);$('draft-remaining').textContent=money(c.balance);addFact($('draft-facts'),'name',data.preferred_name);addFact($('draft-facts'),'duration',`${c.units_worked} ${t(({hourly:'hours',daily:'days',weekly:'weeks',monthly:'months',piece:'pieces'})[c.pay_basis])}`);addFact($('draft-facts'),'rate',money(c.rate_per_unit));addFact($('draft-facts'),'location',data.workplace_location);addFact($('draft-facts'),'employer',data.employer_name);$('draft-statement').textContent=data.original_statement;}
  else{const p=state.draft.payment;$('draft-earned').textContent='—';$('draft-received').textContent=money(p.amount);$('draft-remaining').textContent='—';addFact($('draft-facts'),'paymentDate',p.received_on);addFact($('draft-facts'),'paymentMethod',t(p.method==='unknown'?'unknown':p.method));$('draft-statement').textContent=p.original_statement;}
  if(intake)window.dispatchEvent(new CustomEvent('haqrecord-calculation',{detail:state.draft.calculation}));
}
function renderCalculationPreview(preview,force=false){
  $('captured-notes').hidden=true;
  const changed=previewRevision!==preview.preview_id;
  const updated=JSON.stringify(calculationPreview)!==JSON.stringify(preview);
  calculationPreview=preview;
  if(!changed&&!updated&&!force&&!$('draft-review').hidden&&!$('preview-editor').hidden)return;
  previewRevision=preview.preview_id;draft=null;lastDraftId='';
  $('empty-review').hidden=true;$('draft-review').hidden=false;$('voice-saved').hidden=true;
  $('preview-editor').hidden=false;$('draft-heading').textContent=t('reviewTitle');$('voice-pin-wrap').hidden=false;$('voice-pin').required=true;
  const c=preview.calculation;$('draft-earned').textContent=money(c.total_earned);$('draft-received').textContent=money(c.payments_received);$('draft-remaining').textContent=money(c.balance);
  $('draft-facts').replaceChildren();addFact($('draft-facts'),'duration',`${c.units_worked} ${t(({hourly:'hours',daily:'days',weekly:'weeks',monthly:'months',piece:'pieces'})[c.pay_basis])}`);addFact($('draft-facts'),'rate',money(c.rate_per_unit));$('draft-statement').textContent='';
  $('approve-voice-button').querySelector('span').textContent=t('saveCase');
  if(changed||updated){$('preview-story').value=preview.original_statement||'';$('preview-name').value=preview.preferred_name||'';$('preview-location').value=preview.workplace_location||'';$('preview-employer').value=preview.employer_name||'';$('approve-voice').checked=false;$('voice-pin').value='';$('distinct-payment').checked=false;$('distinct-wrap').hidden=true;notify('approval-message','');notify('voice-message','');}
  window.dispatchEvent(new CustomEvent('haqrecord-calculation',{detail:preview.calculation}));
}
function renderVoiceSaved(result){$('captured-notes').hidden=true;savedVoiceResult=result;$('empty-review').hidden=true;$('draft-review').hidden=true;$('voice-saved').hidden=false;$('voice-saved-reference').textContent=t('caseReference')+': '+(result.case?.case_id||'');if(result.case){caseRecord=result.case;window.dispatchEvent(new CustomEvent('haqrecord-case-saved',{detail:result.case}));}}
async function refreshVoice(){
  if(polling||savingVoice)return;polling=true;
  const requestedLanguage=language;
  try{const response=await fetch('/voice/intake/state?language='+requestedLanguage);if(!response.ok)return;const state=await response.json();if(savingVoice||requestedLanguage!==language)return;voiceCsrf=state.csrf_token;if(state.resources)renderResources(state.resources);
    if(state.resources&&!state.next_step&&state.state!=='saved')window.dispatchEvent(new CustomEvent('haqrecord-resources',{detail:state.resources}));
    if(state.next_step)window.dispatchEvent(new CustomEvent('haqrecord-next-step',{detail:state.next_step}));
    if(state.state==='saved'&&state.result)renderVoiceSaved(state.result);
    else if(state.state==='awaiting_browser_approval'&&state.draft)renderDraft(state);
    else if(state.preview)renderCalculationPreview(state.preview);
    else{
      calculationPreview=null;previewRevision='';draft=null;lastDraftId='';
      $('approve-voice').checked=false;$('voice-pin').value='';
      $('draft-review').hidden=true;$('voice-saved').hidden=true;
      if(state.notes)renderAccountNotes(state.notes);
      else{$('captured-notes').hidden=true;$('empty-review').hidden=false;}
      if(state.state==='needs_clarification')notify('voice-message',t('clarifyFigures'));
    }
  }finally{polling=false;}
}
async function launchCall(){
  if(busy||!voiceReady||!$('voice-consent').checked)return;
  if(!window.isSecureContext||typeof BolnaWebCall==='undefined'){notify('voice-message',t('serviceUnavailable'));return;}
  if(window.HaqReadAloud)window.HaqReadAloud.stop();else if('speechSynthesis' in window)speechSynthesis.cancel();notify('voice-message','');busy=true;callState='connecting';updateCall();
  // Request microphone permission BEFORE minting a short-lived provider
  // session. Failure here must not use a paid session or a daily request slot.
  try{const probe=await navigator.mediaDevices.getUserMedia({audio:microphoneConstraints(),video:false});probe.getTracks().forEach(track=>track.stop());}
  catch(error){busy=false;callState='ready';updateCall();notify('voice-message',humanError(error));return;}
  call=new BolnaWebCall({audio:microphoneConstraints(),getSession:async()=>{
    const response=await fetch('/voice/intake/session',{method:'POST',headers:{'Content-Type':'application/json',...(voiceMode==='existing'&&workerSession?{'X-CSRF-Token':workerSession.csrf_token}:{})},body:JSON.stringify({consent_to_voice_processing:true,mode:voiceMode,language})});
    const data=await response.json();if(!response.ok){const error=new Error('Connection failed');error.status=response.status;error.code=data.detail?.code;throw error;}
    voiceCsrf=response.headers.get('X-Voice-CSRF')||'';accountNotes=null;$('captured-notes').hidden=true;calculationPreview=null;previewRevision='';draft=null;lastDraftId='';savedVoiceResult=null;$('empty-review').hidden=false;$('draft-review').hidden=true;$('voice-saved').hidden=true;window.dispatchEvent(new CustomEvent('haqrecord-next-step',{detail:null}));return data;
  }});
  call.on('state-change',state=>{callState=state==='active'?'active':state==='ringing'?'ringing':state==='ended'?'ended':'connecting';updateCall();});
  call.on('call-start',()=>{callState='active';updateCall();startCallAudioHealth();if(micCheckActive)restartMicrophoneCheck();});
  call.on('call-end',({reason}={})=>{stopCallAudioHealth();if(micCheckActive&&!micCheckOwnsStream)restartMicrophoneCheck();clearTimeout(timer);busy=false;callState='ended';updateCall();if(reason==='remote-hangup'&&!$('voice-message').textContent)notify('voice-message',t('voiceDisconnected'));refreshVoice().catch(()=>{});if(voiceCsrf)api('/voice/intake/end','POST',null,voiceCsrf).catch(()=>{});});
  call.on('error',error=>notify('voice-message',humanError(error)));
  try{await call.start();}catch(error){notify('voice-message',humanError(error));try{await call.stop();}catch{}busy=false;callState='ended';updateCall();}
}
let stopAudioHealth=null;
function stopCallAudioHealth(){if(stopAudioHealth)stopAudioHealth();stopAudioHealth=null;const node=document.getElementById('call-audio-health');if(node)node.hidden=true;}
async function restartMicrophoneCheck(){const generation=micCheckGeneration+1;await stopMicrophoneCheck();if(micCheckGeneration===generation&&$('voice-consent').checked)await checkMicrophone();}
function startCallAudioHealth(){
  stopCallAudioHealth();if(!window.HaqCallAudio)return;
  let node=document.getElementById('call-audio-health');
  if(!node){node=document.createElement('p');node.id='call-audio-health';node.className='quiet-note';node.setAttribute('role','status');$('check-microphone').parentNode.append(node);}
  node.hidden=false;
  stopAudioHealth=HaqCallAudio.watch(call,health=>{
    const en={checking:'Checking outgoing call audio...',sending:'Audio packets are leaving your browser. This does not confirm Sara has transcribed your words.',stalled:'Outgoing call audio has stalled. Your local microphone bar can still move.',missing:'The call has no outgoing microphone track. End the call and reconnect.',muted:'The call microphone is muted or unavailable. Check your selected input.',unknown:'Unable to verify outgoing call audio.'};
    const hi={checking:'\u0915\u0949\u0932 \u0915\u0940 \u0906\u0935\u093e\u091c\u093c \u091c\u093e\u0902\u091a \u0930\u0939\u0947 \u0939\u0948\u0902...',sending:'\u0906\u0935\u093e\u091c\u093c \u092c\u094d\u0930\u093e\u0909\u091c\u093c\u0930 \u0938\u0947 \u092d\u0947\u091c\u0940 \u091c\u093e \u0930\u0939\u0940 \u0939\u0948\u0964 \u0907\u0938\u0938\u0947 \u0938\u093e\u0930\u093e \u0926\u094d\u0935\u093e\u0930\u093e \u0936\u092c\u094d\u0926 \u0932\u093f\u0916\u0928\u0947 \u0915\u0940 \u092a\u0941\u0937\u094d\u091f\u093f \u0928\u0939\u0940\u0902 \u0939\u094b\u0924\u0940\u0964'};
    node.textContent=(language==='hi'&&hi[health.state])||en[health.state];
  });
}
function balanceSpeech(calculation){return `${t('earned')} ${calculation.total_earned}. ${t('received')} ${calculation.payments_received}. ${t('remaining')} ${calculation.balance}. ${t('accountNote')}`;}
async function approveDraft(event){
  event.preventDefault();if(savingVoice||(!draft&&!calculationPreview)||!$('approve-voice').checked)return;
  savingVoice=true;$('approve-voice-button').disabled=true;
  try{if(!draft&&calculationPreview){
      if(!$('preview-story').value.trim()){notify('approval-message',t('required'));$('preview-story').focus();return;}
      if(!$('approve-voice').checked)return;
      const proposal=await api('/voice/intake/prepare-preview','POST',{preview_id:calculationPreview.preview_id,preferred_name:$('preview-name').value.trim()||t('genericWorker'),original_statement:$('preview-story').value,workplace_location:$('preview-location').value||null,employer_name:$('preview-employer').value||null,language,approved:true},voiceCsrf);
      draft={draft_id:proposal.draft_id,draft_kind:'intake',draft:{intake:{original_statement:$('preview-story').value},calculation:calculationPreview.calculation}};
    }
    const body={draft_id:draft.draft_id,approved:true,distinct_payment_confirmed:$('distinct-payment').checked};if(draft.draft_kind==='intake')body.pin=$('voice-pin').value;
    const result=await api('/voice/intake/confirm','POST',body,voiceCsrf);$('voice-pin').value='';if(result.session)workerSession=result.session;renderVoiceSaved(result);
  }catch(error){notify('approval-message',humanError(error));if(error.code==='possible_duplicate')$('distinct-wrap').hidden=false;}
  finally{savingVoice=false;$('approve-voice-button').disabled=false;}
}
function questionLabel(question){if(/Employer or contractor/.test(question))return t('unknownEmployer');if(/Workplace location|work location/i.test(question))return t('unknownLocation');if(/dates/.test(question))return t('unknownDates');if(/Advance|deductions/.test(question))return t('checkedAdjustments');if(/reminder|callback/.test(question))return t('unknownReminders');return question;}
function renderCase(data){
  caseRecord=data;$('case-name').textContent=data.intake.preferred_name;$('saved-reference').textContent=t('caseReference')+': '+data.case_id;
  const remainingLabel=$('case-remaining').previousElementSibling;
  if(remainingLabel)remainingLabel.textContent=data.calculation.provisional?(language==='hi'?'अनिश्चित भुगतान से पहले बाकी':'Remaining before unclear payments'):t('remaining');
  if(data.workspace?.pilot_city)$('resource-city').value=data.workspace.pilot_city;
  $('case-earned').textContent=money(data.calculation.total_earned);$('case-received').textContent=money(data.calculation.payments_received);$('case-remaining').textContent=money(data.calculation.balance);$('case-statement').textContent=data.intake.original_statement;
  $('case-questions').replaceChildren();for(const question of data.unresolved_questions){const item=document.createElement('li');item.textContent=questionLabel(question);$('case-questions').append(item);}
  $('case-history').replaceChildren();const initial=document.createElement('li');initial.textContent=`${t('initialPayment')}: ${money(data.intake.payments_received)}. ${t('initialBalance')}: ${money(data.original_calculation.balance)}.`;$('case-history').append(initial);
  for(const payment of data.follow_up_payments){const item=document.createElement('li');item.textContent=`${t('newPayment')}: ${money(payment.amount)} · ${payment.received_on||t('unknown')} · ${t('remaining')}: ${money(payment.updated_balance)}`;$('case-history').append(item);}
  window.dispatchEvent(new CustomEvent('haqrecord-case',{detail:data}));
}
async function showMyCase(){
  if(!workerSession){afterAccess='case';showScreen('access');return;}
  try{renderCase(await api('/worker/my-case'));showScreen('case');}catch(error){workerSession=null;afterAccess='case';showScreen('access');notify('access-message',humanError(error));}
}
async function openCase(event){
  event.preventDefault();$('open-case').disabled=true;notify('access-message','');
  try{workerSession=await api('/worker/login','POST',{case_id:$('case-reference').value.trim(),pin:$('access-pin').value});$('access-pin').value='';caseRecord=await api('/worker/my-case');if(afterAccess==='payment')startVoice('existing');else{renderCase(caseRecord);showScreen('case');}}
  catch(error){notify('access-message',humanError(error));}finally{$('open-case').disabled=false;}
}
function updateTextStep(){
  document.querySelectorAll('.text-step').forEach(section=>section.hidden=Number(section.dataset.step)!==textStep);
  $('text-step-title').textContent=t('textTitles')[textStep];$('text-progress').textContent=language==='hi'?`5 ${t('of')} ${t('step')} ${textStep+1}`:`${t('step')} ${textStep+1} ${t('of')} 5`;
  $('text-progress-bar').style.width=((textStep+1)*20)+'%';$('text-back').hidden=textStep===0;$('text-next').hidden=textStep===4;$('text-save').hidden=textStep!==4;
  $('units-label').textContent=t(({hourly:'hoursWorked',daily:'daysWorked',weekly:'weeksWorked',monthly:'monthsWorked',piece:'piecesWorked'})[$('text-basis').value]);$('rate-label').textContent=t(({hourly:'hourlyRate',daily:'dailyRate',weekly:'weeklyRate',monthly:'monthlyRate',piece:'pieceRate'})[$('text-basis').value]);
  if(textCalculation)$('text-calculation').textContent=`${t('earned')}: ${money(textCalculation.total_earned)} · ${t('received')}: ${money(textCalculation.payments_received)} · ${t('remaining')}: ${money(textCalculation.balance)}`;
}
function textFigures(){return {pay_basis:$('text-basis').value,units_worked:Number($('text-units').value),rate_per_unit:$('text-rate').value,payments_received:$('text-paid').value};}
function validateStep(){const section=document.querySelector(`.text-step[data-step="${textStep}"]`);for(const input of section.querySelectorAll('input,textarea,select')){if(!input.reportValidity())return false;}return true;}
async function nextStep(){
  if(!validateStep())return;notify('text-message','');
  if(textStep===3){try{textCalculation=await api('/calculate','POST',textFigures());}catch(error){notify('text-message',humanError(error));return;}}
  textStep=Math.min(4,textStep+1);updateTextStep();$('text-step-title').scrollIntoView({behavior:'smooth',block:'start'});
}
async function saveText(event){
  event.preventDefault();if(!textCalculation||textStep!==4)return;$('text-save').disabled=true;textOperation ||= crypto.randomUUID();
  try{const result=await api('/worker/cases','POST',{...textFigures(),preferred_name:$('text-name').value.trim()||t('genericWorker'),original_statement:$('text-story').value,language,workplace_location:$('text-location').value||null,employer_name:$('text-employer').value||null,pin:$('text-pin').value,operation_id:textOperation,consent_to_store:$('text-approve').checked,worker_confirmed:$('text-approve').checked});
    workerSession=result.session;textOperation=null;$('text-pin').value='';renderCase(result.case);showScreen('case');
  }catch(error){notify('text-message',humanError(error));}finally{$('text-save').disabled=false;}
}
function downloadReceipt(){if(!caseRecord)return;const c=caseRecord;const text=`HaqRecord\n${t('caseReference')}: ${c.case_id}\n${t('notFiled')}\n\n${t('originalStatement')}\n${c.intake.original_statement}\n\n${t('earned')}: INR ${c.calculation.total_earned}\n${t('received')}: INR ${c.calculation.payments_received}\n${t('remaining')}: INR ${c.calculation.balance}\n\n${t('accountNote')}\n\n${t('stillUnknown')}\n${c.unresolved_questions.map(questionLabel).join('\n')}\n\n${t('paymentHistory')}\n${c.follow_up_payments.map(p=>`${p.received_on||t('unknown')}: INR ${p.amount}; ${t('remaining')}: INR ${p.updated_balance}`).join('\n')}`;
const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));const link=document.createElement('a');link.href=url;link.download=c.case_id+'-receipt.txt';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function bind(){$('text-units').min='0.001';$('text-units').step='0.001';for(const basis of ['hourly','piece']){const option=document.createElement('option');option.value=basis;option.dataset.i18n=basis;$('text-basis').append(option);}$('action-payment').querySelector('use').setAttribute('href','#i-write');
  document.querySelectorAll('svg').forEach(icon=>{icon.setAttribute('aria-hidden','true');icon.setAttribute('focusable','false');});
  $('lang-hi').addEventListener('click',()=>setLanguage('hi'));$('lang-en').addEventListener('click',()=>setLanguage('en'));
  $('listen-guide').addEventListener('click',()=>speak(t(currentScreen==='voice'?'voiceGuide':'guide')));$('listen-voice-help').addEventListener('click',()=>speak(t('voiceGuide')));
  for(const id of ['hero-speak','hero-mic','action-new'])$(id).addEventListener('click',()=>startVoice('new'));
  for(const id of ['hero-type','voice-to-text'])$(id).addEventListener('click',()=>{if(!busy)showScreen('text');else notify('voice-message',t('beforeLeave'));});
  $('action-case').addEventListener('click',showMyCase);$('action-payment').addEventListener('click',()=>window.dispatchEvent(new CustomEvent('haqrecord-open-diary')));
  document.querySelectorAll('[data-home]').forEach(button=>button.addEventListener('click',()=>showScreen('home')));
  $('check-microphone').addEventListener('click',checkMicrophone);
  $('microphone-device').addEventListener('change',async()=>{selectedMicrophone=$('microphone-device').value;await stopMicrophoneCheck();checkMicrophone();});
  window.addEventListener('pagehide',()=>{stopMicrophoneCheck();});
  $('voice-consent').addEventListener('change',()=>{if(!$('voice-consent').checked)stopMicrophoneCheck();updateCall();});$('start-call').addEventListener('click',launchCall);$('stop-call').addEventListener('click',async()=>{if(call)await call.stop();});
  $('approve-voice-form').addEventListener('submit',approveDraft);$('access-form').addEventListener('submit',openCase);
  $('voice-view-case').addEventListener('click',()=>{if(busy){notify('approval-message',t('beforeLeave'));return;}showMyCase();});
  $('read-draft').addEventListener('click',()=>{if(!draft){if(calculationPreview)speak(balanceSpeech(calculationPreview.calculation));return;}if(draft.draft_kind==='intake')speak(balanceSpeech(draft.draft.calculation));else speak(t('newPayment')+' '+draft.draft.payment.amount);});
  $('correct-by-voice').addEventListener('click',()=>{notify('voice-message',busy?t('correctionHint'):(language==='hi'?'कॉल खत्म हो चुकी है। सही जानकारी बताने के लिए नई बातचीत शुरू करें।':'The call has ended. Start a new conversation to provide corrected details.'));});
  $('text-basis').addEventListener('change',()=>{textCalculation=null;updateTextStep();});$('text-next').addEventListener('click',nextStep);$('text-back').addEventListener('click',()=>{textStep=Math.max(0,textStep-1);updateTextStep();});$('text-form').addEventListener('submit',saveText);
  $('text-form').addEventListener('input',()=>{textOperation=null;});
  $('case-speak-payment').addEventListener('click',()=>startVoice('existing'));$('case-listen').addEventListener('click',()=>{if(caseRecord)speak(balanceSpeech(caseRecord.calculation));});$('download-receipt').addEventListener('click',downloadReceipt);
  $('close-case').addEventListener('click',async()=>{try{await api('/worker/logout','POST',null,workerSession?.csrf_token);window.location.replace('/worker');}catch(error){notify('page-message',humanError(error));}});
  document.querySelectorAll('input,textarea,select').forEach(input=>{input.addEventListener('input',()=>input.setCustomValidity(''));input.addEventListener('invalid',()=>{input.setCustomValidity(input.validity.patternMismatch?t('invalidPin'):input.validity.valueMissing?t('required'):t('invalidNumber'));});});
}
async function initialize(){
  $('resource-form').addEventListener('submit',event=>{event.preventDefault();loadResources(false);});
  $('fresh-research').addEventListener('click',()=>loadResources(true));
  bind();setLanguage(language);
  const results=await Promise.allSettled([api('/voice/status'),api('/worker/session')]);
  if(results[0].status==='fulfilled'){voiceReady=Boolean(results[0].value.ready&&results[0].value.backend_connected);voiceConfigurationStatus=results[0].value.agent_configuration||'';voiceConfigurationWarnings=results[0].value.agent_warnings||[];}
  if(results[1].status==='fulfilled')workerSession=results[1].value;
  updateCall();
  if(location.pathname==='/voice')startVoice('new');
  await refreshVoice().catch(()=>{});setInterval(()=>{if(currentScreen==='voice')refreshVoice().catch(()=>{});},2000);
  setInterval(()=>{if(currentScreen==='voice')refreshVoiceAvailability().catch(()=>{});},15000);
}
window.addEventListener('pageshow',event=>{if(event.persisted)window.location.reload();});
initialize().catch(()=>notify('page-message',t('networkError')));
