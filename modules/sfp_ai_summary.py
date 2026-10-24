import json
from spiderfoot import SpiderFootPlugin, SpiderFootEvent

class sfp_ai_summary(SpiderFootPlugin):
    """Summarizes scan findings using an LLM (OpenAI or Gemini)."""
    meta = {
        'name': "AI Threat Intelligence Summarizer",
        'summary': "Summarizes scan findings using an LLM.",
        'flags': ['apikey'],
        'useCases': ["Investigate"],
        'group': ["Investigate"],
        'categories': ["Content Analysis"],
        'dataSource': {
            'name': 'OpenAI / Gemini',
            'summary': 'LLM provider (auto-selected from the configured model name)',
            'model': 'FREE_AUTH_LIMITED',
            'apiKeyInstructions': [
                'For OpenAI: sign up at https://platform.openai.com/ and create an API key.',
                'For Gemini: create a key at https://aistudio.google.com/app/apikey.',
                'Paste the API key into the module configuration, and set model '
                'to a matching name (e.g. gpt-3.5-turbo or gemini-1.5-flash).'
            ]
        }
    }

    opts = {
        "api_key": "",
        "model": "gpt-3.5-turbo",
        "summary_frequency": "on_finish",  # or "periodic"
        "max_events": 100
    }

    optdescs = {
        "api_key": "API key for the LLM provider.",
        "model": "Model name -- provider is inferred from this: any name "
                 "containing 'gemini' calls Google's Gemini API, everything "
                 "else calls OpenAI's (e.g. gpt-3.5-turbo, gemini-1.5-flash).",
        "summary_frequency": "When to summarize: on_finish or periodic.",
        "max_events": "Max events to include in the summary."
    }

    def setup(self, sfc, userOpts=dict()):
        self.sf = sfc
        self.opts.update(userOpts)
        self.event_buffer = []

    def watchedEvents(self):
        return ["*"]

    def producedEvents(self):
        return ["THREAT_INTEL_SUMMARY"]

    def handleEvent(self, event):
        self.event_buffer.append(event)
        if self.opts.get("summary_frequency") == "periodic" and len(self.event_buffer) >= int(self.opts.get("max_events", 100)):
            self._summarize_events()

    def scanFinished(self):
        if self.event_buffer:
            self._summarize_events()

    def _summarize_events(self):
        if not self.opts.get("api_key"):
            self.error("No API key provided for LLM summarization.")
            return

        prompt = "Summarize the following security events:\n"
        for event in self.event_buffer[-int(self.opts["max_events"]):]:
            prompt += f"- {event.eventType}: {event.data}\n"

        model = self.opts.get("model", "")
        try:
            # This used to hardcode openai.ChatCompletion.create() no
            # matter what provider/model was actually configured -- a
            # Gemini key + Gemini model name (as configured live) just
            # failed against OpenAI's API every time, always producing
            # "Summary unavailable due to API error." Infer the provider
            # from the model name instead of assuming OpenAI.
            if "gemini" in model.lower():
                summary = self._summarize_with_gemini(prompt, model)
            else:
                summary = self._summarize_with_openai(prompt, model)
        except Exception as e:
            self.error(f"LLM API error: {e}")
            summary = "Summary unavailable due to API error."

        evt = SpiderFootEvent(
            "THREAT_INTEL_SUMMARY",
            summary,
            self.__class__.__name__,
            None
        )
        self.notifyListeners(evt)
        self.event_buffer = []

    def _summarize_with_gemini(self, prompt: str, model: str) -> str:
        """Call Google's Gemini generateContent REST API directly --
        avoids adding a new SDK dependency (google-generativeai isn't in
        requirements.txt) when this codebase's own fetchUrl() already
        does plain HTTP calls the same way every other module does.
        """
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={self.opts['api_key']}"
        )
        body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]})
        res = self.sf.fetchUrl(
            url,
            postData=body,
            headers={'Content-Type': 'application/json'},
            useragent=self.opts.get('_useragent', 'SpiderFoot'),
            timeout=30
        )
        if not res or res.get('code') != '200':
            raise IOError(
                f"Gemini API returned HTTP {res.get('code') if res else None}: "
                f"{(res.get('content') if res else 'no response')}"
            )
        data = json.loads(res['content'])
        return data['candidates'][0]['content']['parts'][0]['text']

    def _summarize_with_openai(self, prompt: str, model: str) -> str:
        import openai
        openai.api_key = self.opts["api_key"]
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message["content"]
