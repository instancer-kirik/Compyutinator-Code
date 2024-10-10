from collections import defaultdict

class KnowledgeGraph:
    def __init__(self):
        self.clear()

    def clear(self):
        self.links = defaultdict(set)
        self.tags = defaultdict(set)
        self.references = defaultdict(set)
        self.backlinks = defaultdict(set)

    def add_link(self, source, target):
        self.links[source].add(target)
        self.backlinks[target].add(source)

    def add_tag(self, file, tag):
        self.tags[file].add(tag)

    def add_reference(self, file, reference):
        self.references[file].add(reference)

    def get_backlinks(self, file):
        return self.backlinks[file]

    def get_connected_nodes(self, file):
        connected = set()
        connected.update(self.links[file])
        connected.update(self.backlinks[file])
        connected.update(self.tags[file])
        connected.update(self.references[file])
        return connected
    def get_all_tags(self):
        return list(set(tag for tags in self.tags.values() for tag in tags))
    def get_all_references(self):
        return list(set(ref for refs in self.references.values() for ref in refs))
    def get_all_files(self):
        return list(self.links.keys())
    def get_all_backlinks(self):
        return list(set(file for backlinks in self.backlinks.values() for file in backlinks))
    