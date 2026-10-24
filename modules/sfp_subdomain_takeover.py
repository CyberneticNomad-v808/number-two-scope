# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:        sfp_subdomain_takeover
# Purpose:     Check if affiliated subdomains are vulnerable to takeover
#              using the fingerprints.json list from subjack by haccer:
#              - https://github.com/haccer/subjack/master/fingerprints.json
#
# Author:      <bcoles@gmail.com>
#
# Created:     2020-06-21
# Copyright:   (c) bcoles 2020
# Licence:     MIT
# -------------------------------------------------------------------------------

import json

from spiderfoot import SpiderFootEvent, SpiderFootPlugin


class sfp_subdomain_takeover(SpiderFootPlugin):

    meta = {
        'name': "Subdomain Takeover Checker",
        'summary': "Check if affiliated subdomains are vulnerable to takeover.",
        'flags': [],
        'useCases': ["Footprint", "Investigate"],
        'categories': ["Crawling and Scanning"]
    }

    # Default options
    opts = {
    }

    # Option descriptions
    optdescs = {
    }

    results = None
    errorState = False
    fingerprints = dict()

    # Initialize module and module options
    def setup(self, sfc, userOpts=dict()):
        self.sf = sfc
        self.results = self.tempStorage()
        self.errorState = False

        for opt in userOpts.keys():
            self.opts[opt] = userOpts[opt]

        # Cache key changed from "subjack-fingerprints" to
        # "can-i-take-over-xyz-fingerprints" deliberately: the old key had
        # a poisoned 404 response cached under it from before this source
        # swap (the pre-fix code cached fetchUrl()'s result unconditionally,
        # with no HTTP-status check), and cacheGet() runs before any of the
        # fetch/validation logic below -- reusing the old key would keep
        # serving that stale garbage for its full 48h TTL regardless of any
        # fix here, exactly what happened live the first time this shipped.
        content = self.sf.cacheGet("can-i-take-over-xyz-fingerprints", 48)
        if content is None:
            # The original haccer/subjack fingerprints.json this module was
            # written against no longer exists upstream (subjack dropped the
            # separate JSON file entirely). EdOverflow/can-i-take-over-xyz is
            # the actively-maintained equivalent -- same idea (cname/service/
            # fingerprint/nxdomain per entry) but 'fingerprint' is a single
            # string there rather than a list, normalised below.
            url = "https://raw.githubusercontent.com/EdOverflow/can-i-take-over-xyz/master/fingerprints.json"
            res = self.sf.fetchUrl(url, useragent="SpiderFoot")

            if res['content'] is None or res.get('code') != '200':
                self.error(f"Unable to fetch {url} (HTTP {res.get('code')})")
                self.errorState = True
                return

            self.sf.cachePut("can-i-take-over-xyz-fingerprints", res['content'])
            content = res['content']

        try:
            self.fingerprints = json.loads(content)
        except Exception as e:
            self.error(
                f"Unable to parse subdomain takeover fingerprints list: {e}")
            self.errorState = True
            return

        # Normalise 'fingerprint' to always be a list: the current source
        # stores a single string there, but the rest of this module expects
        # to iterate over a list of candidate fingerprint substrings.
        for entry in self.fingerprints:
            fp = entry.get("fingerprint")
            if isinstance(fp, str):
                entry["fingerprint"] = [fp]
            elif fp is None:
                entry["fingerprint"] = []

    # What events is this module interested in for input
    def watchedEvents(self):
        return ["AFFILIATE_INTERNET_NAME", "AFFILIATE_INTERNET_NAME_UNRESOLVED"]

    # What events this module produces
    def producedEvents(self):
        return ["AFFILIATE_INTERNET_NAME_HIJACKABLE"]

    # Handle events sent to this module
    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data

        if self.errorState:
            return

        if eventData in self.results:
            return

        self.results[eventData] = True

        self.debug(f"Received event, {eventName}, from {srcModuleName}")

        if eventName == "AFFILIATE_INTERNET_NAME":
            for data in self.fingerprints:
                service = data.get("service")
                cnames = data.get("cname")
                fingerprints = data.get("fingerprint")
                nxdomain = data.get("nxdomain")

                if nxdomain:
                    continue

                for cname in cnames:
                    if cname.lower() not in eventData.lower():
                        continue

                    for proto in ["https", "http"]:
                        res = self.sf.fetchUrl(
                            f"{proto}://{eventData}/",
                            timeout=15,
                            useragent=self.opts['_useragent'],
                            verify=False
                        )
                        if not res:
                            continue
                        if not res['content']:
                            continue
                        for fingerprint in fingerprints:
                            if fingerprint in res['content']:
                                self.info(
                                    f"{eventData} appears to be vulnerable to takeover on {service}")
                                evt = SpiderFootEvent(
                                    "AFFILIATE_INTERNET_NAME_HIJACKABLE", eventData, self.__name__, event)
                                self.notifyListeners(evt)
                                break

        if eventName == "AFFILIATE_INTERNET_NAME_UNRESOLVED":
            for data in self.fingerprints:
                service = data.get("service")
                cnames = data.get("cname")
                nxdomain = data.get("nxdomain")

                if not nxdomain:
                    continue

                for cname in cnames:
                    if cname.lower() not in eventData.lower():
                        continue
                    self.info(
                        f"{eventData} appears to be vulnerable to takeover on {service}")
                    evt = SpiderFootEvent(
                        "AFFILIATE_INTERNET_NAME_HIJACKABLE", eventData, self.__name__, event)
                    self.notifyListeners(evt)

# End of sfp_subdomain_takeover class
