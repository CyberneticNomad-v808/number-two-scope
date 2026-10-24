import cherrypy
from operator import itemgetter
from spiderfoot import __version__
try:
    from spiderfoot.sflib import SpiderFoot
except ImportError:
    pass

class InfoEndpoints:
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def eventtypes(self):
        cherrypy.response.headers['Content-Type'] = "application/json; charset=utf-8"
        dbh = self.get_dbh()
        types = dbh.eventTypes()
        ret = list()
        for r in types:
            ret.append(r)
        return sorted(ret, key=itemgetter(0))

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def modules(self):
        cherrypy.response.headers['Content-Type'] = "application/json; charset=utf-8"
        modlist = list()
        modules_data = self.config['__modules__']

        # Handle both dict and list formats for backward compatibility
        if isinstance(modules_data, dict):
            # Convert dict to list format expected by frontend
            # modules_data comes from loadModulesAsDict() which returns dicts with keys:
            # 'name', 'descr', 'cats', 'labels', 'provides', 'consumes', 'opts', 'optdescs', 'meta', 'group'
            for mod_name, mod_obj in modules_data.items():
                if isinstance(mod_obj, dict):
                    # mod_obj is a dictionary from loadModulesAsDict
                    mod_dict = {
                        'name': mod_name,
                        'descr': mod_obj.get('descr', '') or mod_obj.get('name', mod_name),
                        'provides': mod_obj.get('provides', []),
                        'consumes': mod_obj.get('consumes', []),
                        'opts': mod_obj.get('opts', {}),
                        'group': mod_obj.get('group', []),  # useCases from meta
                        'cats': mod_obj.get('cats', []),    # categories
                        'labels': mod_obj.get('labels', []) # flags
                    }
                    modlist.append(mod_dict)
                elif hasattr(mod_obj, '__doc__') and hasattr(mod_obj, 'opts'):
                    # mod_obj is an actual module class (legacy support)
                    mod_dict = {
                        'name': mod_name,
                        'descr': mod_obj.__doc__ or 'No description available',
                        'provides': getattr(mod_obj, 'produces', []),
                        'consumes': getattr(mod_obj, 'watchedEvents', []),
                        'opts': getattr(mod_obj, 'opts', {}),
                        'group': getattr(mod_obj, 'meta', {}).get('useCases', []),
                        'cats': getattr(mod_obj, 'meta', {}).get('categories', []),
                        'labels': getattr(mod_obj, 'meta', {}).get('flags', [])
                    }
                    modlist.append(mod_dict)
                else:
                    # Fallback for simple string entries
                    modlist.append({
                        'name': mod_name,
                        'descr': 'Module description not available',
                        'provides': [],
                        'consumes': [],
                        'opts': {},
                        'group': [],
                        'cats': [],
                        'labels': []
                    })
        else:
            # Handle list format (original)
            for mod in modules_data:
                modlist.append(mod)

        # sfp__* (double-underscore) modules are internal plumbing, not
        # user-selectable scan modules -- e.g. sfp__stor_db is force-added
        # to every scan's module list regardless of what the user picked
        # (see workspace.py, webui/scan.py, webui/routes.py), so it was
        # never meant to appear as something a user chooses independently.
        modlist = [m for m in modlist if not m['name'].startswith('sfp__')]

        return sorted(modlist, key=lambda x: x['name'])

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def correlationrules(self):
        cherrypy.response.headers['Content-Type'] = "application/json; charset=utf-8"
        rules = list()
        for rule in self.config.get('__correlationrules__', []):
            rules.append(rule)
        return sorted(rules, key=lambda x: x['name'])

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def ping(self):
        cherrypy.response.headers['Content-Type'] = "application/json; charset=utf-8"
        return ["SUCCESS", __version__]

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def query(self, query):
        dbh = self.get_dbh()
        if not query:
            return ["ERROR", "No query provided"]
        if not query.lower().startswith("select"):
            return ["ERROR", "Only SELECT queries are allowed"]
        try:
            result = dbh.query(query)
            return ["SUCCESS", result]
        except Exception as e:
            return ["ERROR", str(e)]

    def get_dbh(self):
        from spiderfoot import SpiderFootDb
        return SpiderFootDb(self.config)
