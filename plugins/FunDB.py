#!/usr/bin/env python

###
# Copyright (c) 2002, Jeremiah Fincher
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

"""
Provides fun commands that require a database to operate.
"""

from baseplugin import *

import string
import os.path

import sqlite

import conf
import ircmsgs
import ircutils
import privmsgs
import callbacks

dbFilename = os.path.join(conf.dataDir, 'FunDB.db')

def makeDb(dbfilename, replace=False):
    if os.path.exists(dbfilename):
        if replace:
            os.remove(dbfilename)
        else:
            return sqlite.connect(dbfilename)
    db = sqlite.connect(dbfilename)
    cursor = db.cursor()
    cursor.execute("""CREATE TABLE insults (
                      id INTEGER PRIMARY KEY,
                      insult TEXT
                      )""")
    cursor.execute("""CREATE TABLE excuses (
                      id INTEGER PRIMARY KEY,
                      excuse TEXT
                      )""")
    cursor.execute("""CREATE TABLE larts (
                      id INTEGER PRIMARY KEY,
                      lart TEXT
                      )""")
    cursor.execute("""CREATE TABLE praises (
                      id INTEGER PRIMARY KEY,
                      praise TEXT
                      )""")
    cursor.execute("""CREATE TABLE words (
                      id INTEGER PRIMARY KEY,
                      word TEXT UNIQUE ON CONFLICT IGNORE,
                      sorted_word_id INTEGER
                      )""")
    cursor.execute("""CREATE INDEX sorted_word_id ON words (sorted_word_id)""")
    cursor.execute("""CREATE TABLE sorted_words (
                      id INTEGER PRIMARY KEY,
                      word TEXT UNIQUE ON CONFLICT IGNORE
                      )""")
    cursor.execute("""CREATE INDEX sorted_words_word ON sorted_words (word)""")
    db.commit()
    return db

def addWord(db, word, commit=False):
    word = word.strip().lower()
    L = list(word)
    L.sort()
    sorted = ''.join(L)
    cursor = db.cursor()
    cursor.execute("""INSERT INTO sorted_words VALUES (NULL, %s)""", sorted)
    cursor.execute("""INSERT INTO words VALUES (NULL, %s,
                      (SELECT id FROM sorted_words
                       WHERE word=%s))""", word, sorted)
    if commit:
        db.commit()
    

class FunDB(callbacks.Privmsg):
    """
    Contains the 'fun' commands that require a database.  Currently includes
    database-backed commands for crossword puzzle solving, anagram searching,
    larting, excusing, and insulting.
    """
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.db = makeDb(dbFilename)

    def die(self):
        self.db.close()
        
    '''
    def praise(self, irc, msg, args):
        """<something>

        Praises <something> with a praise from my vast database of praises.
        """
        something = privmsgs.getArgs(args)
        if something == 'me':
            something = msg.nick
        elif something == 'yourself':
            something = irc.nick
        cursor = self.db.cursor()
        cursor.execute("""SELECT id, praise FROM praises
                          WHERE praise NOT NULL
                          ORDER BY random()
                          LIMIT 1""")
        (id, insult) = cursor.fetchone()
        s = insul
        irc.queueMsg(ircmsgs.action(ircutils.replyTo(msg),
    '''

    def insult(self, irc, msg, args):
        """<nick>

        Insults <nick>.
        """
        nick = privmsgs.getArgs(args)
        cursor = self.db.cursor()
        cursor.execute("""SELECT id, insult FROM insults
                          WHERE insult NOT NULL
                          ORDER BY random()
                          LIMIT 1""")
        (id, insult) = cursor.fetchone()
        if nick == irc.nick:
            insultee = msg.nick
        else:
            insultee = nick
        if ircutils.isChannel(msg.args[0]):
            means = msg.args[0]
            s = '%s: %s (#%s)' % (insultee, insult, id)
        else:
            means = insultee
            s = insult
        irc.queueMsg(ircmsgs.privmsg(means, s))

    def getinsult(self, irc, msg, args):
        """<id>

        Returns insult #<id>
        """
        id = privmsgs.getArgs(args)
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The id must be an integer.')
            return
        cursor = self.db.cursor()
        cursor.execute("""SELECT insult FROM insults WHERE id=%s""", id)
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such insult.')
        else:
            irc.reply(msg, cursor.fetchone()[0])
            
    def addinsult(self, irc, msg, args):
        """<insult>

        Adds an insult to the insult database.
        """
        insult = privmsgs.getArgs(args)
        cursor = self.db.cursor()
        cursor.execute("""INSERT INTO insults VALUES (NULL, %s)""", insult)
        self.db.commit()
        irc.reply(msg, conf.replySuccess)

    def removeinsult(self, irc, msg, args):
        """<id>

        Removes the insult with id <id> from the insult database.
        """
        id = privmsgs.getArgs(args)
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'You must give a numeric id.')
            return
        cursor = self.db.cursor()
        cursor.execute("""DELETE FROM insults WHERE id=%s""", id)
        self.db.commit()
        irc.reply(msg, conf.replySuccess)

    def numinsults(self, irc, msg, args):
        """takes no arguments

        Returns the number of insults currently in the database.
        """
        cursor = self.db.cursor()
        cursor.execute('SELECT count(*) FROM insults')
        total = cursor.fetchone()[0]
        irc.reply(msg, 'There are currently %s insults in my database' % total)

    def crossword(self, irc, msg, args):
        """<word>

        Gives the possible crossword completions for <word>; use underscores
        ('_') to denote blank spaces.
        """
        word = privmsgs.getArgs(args).lower()
        cursor = self.db.cursor()
        if '%' in word:
            irc.error(msg, '"%" isn\'t allowed in the word.')
            return
        cursor.execute("""SELECT word FROM words
                          WHERE word LIKE %s
                          ORDER BY word""", word)
        words = map(lambda t: t[0], cursor.fetchall())
        irc.reply(msg, ', '.join(words))

    def excuse(self, irc, msg, args):
        """takes no arguments

        Gives you a standard BOFH excuse.
        """
        cursor = self.db.cursor()
        cursor.execute("""SELECT id, excuse FROM excuses
                          WHERE excuse NOTNULL
                          ORDER BY random()
                          LIMIT 1""")
        (id, excuse) = cursor.fetchone()
        irc.reply(msg, '%s (#%s)' % (excuse, id))

    def getexcuse(self, irc, msg, args):
        """<id>

        Gets the excuse with the id number <id>.
        """
        id = privmsgs.getArgs(args)
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The id must be an integer.')
            return
        cursor = self.db.cursor()
        cursor.execute("""SELECT excuse FROM excuses WHERE id=%s""", id)
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such excuse.')
        else:
            irc.reply(msg, cursor.fetchone()[0])
            
    def addexcuse(self, irc, msg, args):
        """<excuse>

        Adds another excuse to the database.
        """
        excuse = privmsgs.getArgs(args)
        cursor = self.db.cursor()
        cursor.execute("""INSERT INTO excuses VALUES (NULL, %s)""", excuse)
        self.db.commit()
        irc.reply(msg, conf.replySuccess)

    def removeexcuse(self, irc, msg, args):
        """<id>

        Removes the excuse with the id number <id> from the database.
        """
        id = privmsgs.getArgs(args)
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'You must give a numeric id.')
            return
        cursor = self.db.cursor()
        cursor.execute("""DELETE FROM excuses WHERE id=%s""", id)
        self.db.commit()
        irc.reply(msg, conf.replySuccess)
    
    def numexcuses(self, irc, msg, args):
        """takes no arguments

        Returns the number of excuses currently in the database.
        """
        cursor = self.db.cursor()
        cursor.execute('SELECT count(*) FROM excuses')
        total = cursor.fetchone()[0]
        irc.reply(msg, 'There are currently %s excuses in my database' % total)

    def lart(self, irc, msg, args):
        """[<channel>] <nick>

        The <channel> argument is only necessary if the message isn't being
        sent in the channel itself.  Uses a lart on <nick>.
        """
        channel = privmsgs.getChannel(msg, args)
        nick = privmsgs.getArgs(args)
        cursor = self.db.cursor()
        cursor.execute("""SELECT id, lart FROM larts
                          WHERE lart NOTNULL
                          ORDER BY random()
                          LIMIT 1""")
        (id, lart) = cursor.fetchone()
        if nick == irc.nick:
            lartee = msg.nick
        else:
            lartee = nick
        lart = lart.replace("$who", lartee)
        irc.queueMsg(ircmsgs.action(channel, '%s (#%s)' % (lart, id)))

    def getlart(self, irc, msg, args):
        """<id>

        Gets the lart with the id number <id>.
        """
        id = privmsgs.getArgs(args)
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'The id must be an integer.')
            return
        cursor = self.db.cursor()
        cursor.execute("""SELECT lart FROM larts WHERE id=%s""", id)
        if cursor.rowcount == 0:
            irc.error(msg, 'There is no such lart.')
        else:
            irc.reply(msg, cursor.fetchone()[0])
            
    def addlart(self, irc, msg, args):
        """<lart>

        The target of the lart is represented with '$who'.  And example might
        be "addlart chops $who in half with an AOL cd."
        """
        lart = privmsgs.getArgs(args)
        if lart.find('$who') == -1:
            irc.error(msg, 'There must be an $who in the lart somewhere.')
            return
        cursor = self.db.cursor()
        cursor.execute("""INSERT INTO larts VALUES (NULL, %s)""", lart)
        self.db.commit()
        irc.reply(msg, conf.replySuccess)

    def removelart(self, irc, msg, args):
        """<id>

        Removes the lart with id number <id> from the database.
        """
        id = privmsgs.getArgs(args)
        try:
            id = int(id)
        except ValueError:
            irc.error(msg, 'You must give a numeric id.')
            return
        cursor = self.db.cursor()
        cursor.execute("""DELETE FROM larts WHERE id=%s""", id)
        self.db.commit()
        irc.reply(msg, conf.replySuccess)

    def numlarts(self, irc, msg, args):
        """takes no arguments
        
        Returns the number of larts currently in the database.
        """
        cursor = self.db.cursor()
        cursor.execute('SELECT count(*) FROM larts')
        total = cursor.fetchone()[0]
        irc.reply(msg, 'There are currently %s larts in my database' % total)

    def addword(self, irc, msg, args):
        """<word>

        Adds a word to the database of words.  This database is used for the
        anagram and crossword commands.
        """
        word = privmsgs.getArgs(args)
        if word.translate(string.ascii, string.ascii_letters) != '':
            irc.error(msg, 'Word must contain only letters')
        addWord(self.db, word, commit=True)
        irc.reply(msg, conf.replySuccess)

    def anagram(self, irc, msg, args):
        """<word>

        Using the words database, determines if a word has any anagrams.
        """
        word = privmsgs.getArgs(args).strip().lower()
        cursor = self.db.cursor()
        cursor.execute("""SELECT words.word FROM words
                          WHERE sorted_word_id=(
                                SELECT sorted_word_id FROM words
                                WHERE word=%s)""", word)
        words = map(lambda t: t[0], cursor.fetchall())
        try:
            words.remove(word)
        except ValueError:
            pass
        if words:
            irc.reply(msg, ', '.join(words))
        else:
            irc.reply(msg, 'That word has no anagrams that I know of.')
        
Class = FunDB


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print 'Usage: %s <words|larts|excuses|insults> file' % sys.argv[0]
        sys.exit(-1)
    category = sys.argv[1]
    filename = sys.argv[2]
    db = makeDb(dbFilename)
    cursor = db.cursor()
    for line in open(filename, 'r'):
        line = line.rstrip()
        if not line:
            continue
        if category == 'words':
            cursor.execute("""PRAGMA cache_size = 50000""")
            addWord(db, line)
        elif category == 'larts':
            if line.find('$who') != -1:
                cursor.execute("""INSERT INTO larts VALUES (NULL, %s)""", line)
            else:
                print 'Invalid lart: %s' % line
        elif category == 'insults':
            cursor.execute("""INSERT INTO insults VALUES (NULL, %s)""", line)
        elif category == 'excuses':
            cursor.execute("""INSERT INTO excuses VALUES (NULL, %s)""", line)
    db.commit()
    db.close()
            
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78: 
