"""
The Orgnode module consists of the Orgnode class for representing a
headline and associated text from an org-mode file, and routines for
constructing data structures of these classes.
"""

import re, sys
import datetime
import codecs


def get_datetime(year, month, day, hour=None, minute=None, second=None):
    if "" in (year, month, day):
        raise ValueError ("First three arguments must not contain empty str")
    if None in (year, month, day):
        raise ValueError ("First three arguments must not contain None")

    ymdhms = []
    for a in [year, month, day, hour, minute, second]:
        if a != None and a != "":
            ymdhms.append(int(a))

    if len(ymdhms) > 3:
        return datetime.datetime(*ymdhms)
    else:
        return datetime.date(*ymdhms)

def _re_compile_date():
    """
    >>> re_date = _re_compile_date()
    >>> re_date.match('')
    >>> m = re_date.match('<2010-06-21 Mon>')
    >>> m.group()
    '<2010-06-21 Mon>'
    >>> m.group(1)
    >>> m.group(16)
    '<2010-06-21 Mon>'
    >>> m = re_date.match('<2010-06-21 Mon 12:00>--<2010-06-21 Mon 12:00>')
    >>> m.group()
    '<2010-06-21 Mon 12:00>--<2010-06-21 Mon 12:00>'
    >>> m.group(1)
    '<2010-06-21 Mon 12:00>--<2010-06-21 Mon 12:00>'
    >>> m.group(16)
    """
    date_pattern = "<(\d+)\-(\d+)\-(\d+)([^>\d]*)((\d+)\:(\d+))?>"
    re_date = re.compile('(%(dtp)s--%(dtp)s)|(%(dtp)s)'
                         % dict(dtp=date_pattern))
    return re_date

_RE_DATE = _re_compile_date()

def get_daterangelist(string):
    datelist = []
    rangelist = []
    for dm in _RE_DATE.findall(string):
        if dm[0]:
            d1 = get_datetime(dm[1], dm[2], dm[3], dm[6], dm[7])
            d2 = get_datetime(dm[8], dm[9], dm[10], dm[13], dm[14])
            rangelist.append((d1, d2))
        else:
            dt = get_datetime(dm[16], dm[17], dm[18], dm[21], dm[22])
            datelist.append(dt)
    return (datelist, rangelist)


def makelist(filename, todo_default=['TODO', 'DONE']):
    """
    Read an org-mode file and return a list of Orgnode objects
    created from this file.
    """
    ctr = 0

    try:
        f = codecs.open(filename, 'r')
    except IOError:
        print "Unable to open file [%s] " % filename
        print "Program terminating."
        sys.exit(1)

    todos = set(todo_default) # populated from #+SEQ_TODO line
    level         = 0
    heading       = ""
    bodytext      = ""
    tag1          = ""      # The first tag enclosed in ::
    alltags       = set([]) # set of all tags in headline
    sched_date    = ''
    deadline_date = ''
    datelist      = []
    rangelist     = []
    nodelist      = []
    propdict      = dict()

    for line in f:
        ctr += 1
        hdng = re.search('^(\*+)\s(.*?)\s*$', line)
        if hdng:
            if heading:  # we are processing a heading line
                thisNode = Orgnode(level, heading, bodytext, tag1, alltags)
                if sched_date:
                    thisNode.setScheduled(sched_date)
                    sched_date = ""
                if deadline_date:
                    thisNode.setDeadline(deadline_date)
                    deadline_date = ''
                if datelist:
                    thisNode.setDateList(datelist)
                    datelist = []
                if rangelist:
                    thisNode.setRangeList(rangelist)
                    rangelist = []
                thisNode.setProperties(propdict)
                nodelist.append( thisNode )
                propdict = dict()
            level = hdng.group(1)
            heading =  hdng.group(2)
            bodytext = ""
            tag1 = ""
            alltags = set() # set of all tags in headline
            tagsrch = re.search('(.*?)\s*:(.*?):(.*?)$',heading)
            if tagsrch:
                heading = tagsrch.group(1)
                tag1 = tagsrch.group(2)
                alltags.add(tag1)
                tag2 = tagsrch.group(3)
                if tag2:
                    alltags |= set(tag2.split(':')) - set([''])
        else:      # we are processing a non-heading line
            if line[:10] == '#+SEQ_TODO':
                todos |= set(re.findall(' ([A-Z][A-Z0-9]+)\(?', line))

            if line[:1] != '#':
                bodytext = bodytext + line

            if re.search(':PROPERTIES:', line): continue
            if re.search(':END:', line): continue
            prop_srch = re.search('^\s*:(.*?):\s*(.*?)\s*$', line)
            if prop_srch:
                propdict[prop_srch.group(1)] = prop_srch.group(2)
                continue
            sd_re = re.search(
               'SCHEDULED:\s+<(\d+)\-(\d+)\-(\d+)[^>\d]*((\d+)\:(\d+))?>', line)
            if sd_re:
                if sd_re.group(4) == None:
                    sched_date = datetime.date(int(sd_re.group(1)),
                                               int(sd_re.group(2)),
                                               int(sd_re.group(3)) )
                else:
                    sched_date = datetime.datetime(int(sd_re.group(1)),
                                                   int(sd_re.group(2)),
                                                   int(sd_re.group(3)),
                                                   int(sd_re.group(5)),
                                                   int(sd_re.group(6)) )
            dd_re = re.search(
               'DEADLINE:\s+<(\d+)\-(\d+)\-(\d+)[^>\d]*((\d+)\:(\d+))?>', line)
            if dd_re:
                if dd_re.group(4) == None:
                    deadline_date = datetime.date(int(dd_re.group(1)),
                                                  int(dd_re.group(2)),
                                                  int(dd_re.group(3)) )
                else:
                    deadline_date = datetime.datetime(int(dd_re.group(1)),
                                                      int(dd_re.group(2)),
                                                      int(dd_re.group(3)),
                                                      int(dd_re.group(5)),
                                                      int(dd_re.group(6)) )
            if not sd_re and not dd_re:
                (dl, rl) = get_daterangelist(line)
                datelist += dl
                rangelist += rl

    # write out last node
    thisNode = Orgnode(level, heading, bodytext, tag1, alltags)
    thisNode.setProperties(propdict)
    if sched_date:
        thisNode.setScheduled(sched_date)
    if deadline_date:
        thisNode.setDeadline(deadline_date)
    nodelist.append( thisNode )

    # using the list of TODO keywords found in the file
    # process the headings searching for TODO keywords
    for n in nodelist:
        h = n.Heading()
        todoSrch = re.search('([A-Z][A-Z0-9]+)\s(.*?)$', h)
        if todoSrch:
            if todoSrch.group(1) in todos:
                n.setHeading( todoSrch.group(2) )
                n.setTodo ( todoSrch.group(1) )
        prtysrch = re.search('^\[\#(A|B|C)\] (.*?)$', n.Heading())
        if prtysrch:
            n.setPriority(prtysrch.group(1))
            n.setHeading(prtysrch.group(2))

    # set parent of nodes
    ancestors = [None]
    n1 = nodelist[0]
    l1 = n1.Level()
    for n2 in nodelist:
        # n1, l1: previous node and its level
        # n2, l2: this node and its level
        l2 = n2.Level()
        if l1 < l2:
            ancestors.append(n1)
        else:
            while len(ancestors) > l2:
                ancestors.pop()
        n2.setParent(ancestors[-1])
        n1 = n2
        l1 = l2

    return nodelist

######################
class Orgnode(object):
    """
    Orgnode class represents a headline, tags and text associated
    with the headline.
    """
    def __init__(self, level, headline, body, tag, alltags):
        """
        Create an Orgnode object given the parameters of level (as the
        raw asterisks), headline text (including the TODO tag), and
        first tag. The makelist routine postprocesses the list to
        identify TODO tags and updates headline and todo fields.
        """
        self.level = len(level)
        self.headline = headline
        self.body = body
        self.tag = tag            # The first tag in the list
        self.tags = set(alltags)  # All tags in the headline
        self.todo = ""
        self.prty = ""            # empty of A, B or C
        self.scheduled = ""       # Scheduled date
        self.deadline = ""        # Deadline date
        self.properties = dict()
        self.datelist = []
        self.rangelist = []
        self.parent = None

        # Look for priority in headline and transfer to prty field

    def Heading(self):
        """
        Return the Heading text of the node without the TODO tag
        """
        return self.headline

    def setHeading(self, newhdng):
        """
        Change the heading to the supplied string
        """
        self.headline = newhdng

    def Body(self):
        """
        Returns all lines of text of the body of this node except the
        Property Drawer
        """
        return self.body

    def Level(self):
        """
        Returns an integer corresponding to the level of the node.
        Top level (one asterisk) has a level of 1.
        """
        return self.level

    def Priority(self):
        """
        Returns the priority of this headline: 'A', 'B', 'C' or empty
        string if priority has not been set.
        """
        return self.prty

    def setPriority(self, newprty):
        """
        Change the value of the priority of this headline.
        Values values are '', 'A', 'B', 'C'
        """
        self.prty = newprty

    def Tag(self):
        """
        Returns the value of the first tag.
        For example, :HOME:COMPUTER: would return HOME
        """
        return self.tag

    def Tags(self, inher=False):
        """
        Returns a list of all tags
        For example, :HOME:COMPUTER: would return ['HOME', 'COMPUTER']
        If `inher` is True, then all tags from ancestors is included.
        """
        if inher and self.parent:
            return self.tags | set(self.parent.Tags(True))
        else:
            return self.tags

    def hasTag(self, srch):
        """
        Returns True if the supplied tag is present in this headline
        For example, hasTag('COMPUTER') on headling containing
        :HOME:COMPUTER: would return True.
        """
        return srch in self.tags

    def setTag(self, newtag):
        """
        Change the value of the first tag to the supplied string
        """
        self.tag = newtag

    def setTags(self, taglist):
        """
        Store all the tags found in the headline. The first tag will
        also be stored as if the setTag method was called.
        """
        self.tags |= set(taglist)

    def Todo(self):
        """
        Return the value of the TODO tag
        """
        return self.todo

    def setTodo(self, value):
        """
        Set the value of the TODO tag to the supplied string
        """
        self.todo = value

    def setProperties(self, dictval):
        """
        Sets all properties using the supplied dictionary of
        name/value pairs
        """
        self.properties = dictval

    def Properties(self):
        """
        Return the value of the properties.
        """
        return self.properties

    def Property(self, keyval):
        """
        Returns the value of the requested property or null if the
        property does not exist.
        """
        return self.properties.get(keyval, "")

    def setScheduled(self, dateval):
        """
        Set the scheduled date using the supplied date object
        """
        self.scheduled = dateval

    def Scheduled(self):
        """
        Return the scheduled date object or null if nonexistent
        """
        return self.scheduled

    def setDeadline(self, dateval):
        """
        Set the deadline (due) date using the supplied date object
        """
        self.deadline = dateval

    def Deadline(self):
        """
        Return the deadline date object or null if nonexistent
        """
        return self.deadline

    def setDateList(self, datelist):
        """
        Set the list of date using list of the supplied date object
        """
        self.datelist = datelist[:]

    def DateList(self):
        """
        Return the list of all date as date object
        """
        return self.datelist[:]

    def setRangeList(self, rangelist):
        """
        Set the list of date range using list of the supplied timedelta object
        """
        self.rangelist = rangelist[:]

    def RangeList(self):
        """
        Return the list of all date as date object
        """
        return self.rangelist[:]

    def hasDate(self):
        return (bool(self.scheduled) or
                bool(self.deadline) or
                bool(self.datelist) or
                bool(self.rangelist) )

    def setParent(self, parent):
        """
        Set parent node
        """
        self.parent = parent

    def Parent(self):
        """
        Return parent node if exist else None.
        """
        return self.parent

    def __repr__(self):
        """
        Print the level, heading text and tag of a node and the body
        text as used to construct the node.
        """
        # This method is not completed yet.
        n = ''
        for i in range(0, self.level):
            n = n + '*'
        n = n + ' ' + self.todo + ' '
        if self.prty:
            n = n +  '[#' + self.prty + '] '
        n = n + self.headline
        n = "%-60s " % n     # hack - tags will start in column 62
        closecolon = ''
        for t in sorted(self.tags):
            n = n + ':' + t
            closecolon = ':'
        n = n + closecolon
# Need to output Scheduled Date, Deadline Date, property tags The
# following will output the text used to construct the object
        n = n + "\n" + self.body

        return n
