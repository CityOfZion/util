import os
import re
from google.cloud import translate
import sys

"""commentStripper.py

This script can be used to automatically strip, format, and translate comments
in code for the Antshares/NEO code base using the Google Cloud API.  The script
serially scans, parsers, and translates comments in a file that have the
following structures:

Examples:
    
    <summary>
      This is an example comment.
    </summary>

    <summary>
      <en>
        This is an example comment.
      </en>
    </summary>

Translation can occur to/from any language supported by the Google Translate API
and the starting language does not need to be defined.  The output format is similar
to the second example above.

Refer to the link below for information about configuring the Google Cloud API:
    https://cloud.google.com/translate/docs/getting-started

Args:
    (str): The directory for scan and translate.


Todo:
    * Add multiline comment outputs
"""


ROOT = sys.argv[1]

TAGS = {'main': 'summary',
        'languages': [
            {'language': 'english', 'tag': 'en'},
            {'language': 'chinese', 'tag': 'zh-CN'},
            {'language': 'spanish', 'tag': 'es'}
        ]
      }
"""dict: primary configuration for the translation activity"""


def texasRanger(ROOT):
    """Scans a directory for strings matching the comment format.

    The textRanger function walks a directory and builds up an 
    list of comments that it finds.

    Args:
        ROOT (str): The directory to scan

    Returns:
        (list) A list of comments found in the directory.

            Example:
            
                [{file (str): the path to the file containing the comment,
                  languages: [],
                  index: (int): the base indent size for each row of the comments,
                  raw (str): the raw text of the comment that will be parsed}]
    """
    comments = []
    for dirName, subdirList, fileList in os.walk(ROOT):
        for f in fileList:
            with open('{1}/{2}'.format(ROOT,dirName, f)) as myFile:
                payload = myFile.read()
                if '<{0}>'.format(TAGS['main']) in payload:
                    while (True):
                        if '<{0}>'.format(TAGS['main']) in payload:
                            can = {'file': '{0}/{1}'.format(dirName, f),
                                   'languages': []}
                            start = payload.index('/// <{0}>'.format(TAGS['main'])) 
                            can['index'] = payload[0:start][::-1].index('\n')                           
                            end = payload.index('</{0}>'.format(TAGS['main']))

                            can['raw'] =  payload[start:end + len('</{0}>'.format(TAGS['main']))]
                            comments.append(can)

                            payload = payload[end + 1:]
                        else:
                            break 
    return comments 
                




def parser(comment):
    """Parses the root comment and any existing comments into the comment object
   
    Args:
        comment (dict) The comment object that needs to be parsed.

    Returns:
        (dict) The comment object with the parsed comment.
    """

    scrubbed = comment['raw'].replace('/// <{0}>'.format(TAGS['main']),'').replace('/// </{0}>'.format(TAGS['main']),'').replace('///','')
    scrubbed = scrubbed.replace('\r', '')
    for lang in TAGS['languages']:

        res = re.search('<{0}>.*</{0}>'.format(lang['tag']), scrubbed, re.DOTALL)
        if res:
            c = res.group(0).replace('<{0}>'.format(lang['tag']),'').replace('</{0}>'.format(lang['tag']),'').split('\n')
            c = ' '.join([C.strip() for C in c])
            comment['languages'].append({'language': lang['language'],
                                         'tag':  lang['tag'], 
                                         'comment': c})
            scrubbed = scrubbed.replace(res.group(0), '').strip().strip('\r\n')


    if (len(scrubbed) != 0) and (len(comment['languages']) == 0):
        lang = translate_client.detect_language([scrubbed])[0]
        l = ''
        l = [x['language'] for x in TAGS['languages'] if x['tag'] == lang['language']][0] 
           
        c = scrubbed.strip().split('\n')
        c = ' '.join([C.strip() for C in c])

        can = {'language': l,
               'tag': lang['language'],
               'comment': c}
        comment['languages'].append(can)
         
    return comment       


        
def patcher(comment):
    """The patcher fills in languages that do not already exist in the comment

    Args:
        comment (dict): The comment object that needs to be patched

    Returns:
        (dict): The comment object with all required languages.
    
    """

    found = [x['tag'] for x in comment['languages']]
    missing = [x for x in TAGS['languages'] if x['tag'] not in found]

    for m in missing:
        translation = translate_client.translate(
            comment['languages'][0]['comment'],
            target_language = m['tag'])
        
        can = {'language': m['language'],
               'tag': m['tag'],
               'comment': translation['translatedText'].encode("utf8")}

        comment['languages'].append(can)
    return comment       


def update(comment):
    """The update function executes a string replace on the document to update the comment.

    Args:
        comment (dict): the comment object that will replace the existing comment string
    """

    f = open(comment['file'])
    data = f.read()

    newComment = ''
    for l in comment['languages']:
        newComment += '{2}///   <{0}>\n{2}///     {1}\n{2}///   </{0}>\n'.format(l['tag'], l['comment'], ' ' * comment['index'])
    
    newComment = '/// <summary>\n{0}{1}/// </summary>'.format(newComment, ' ' * comment['index'])

    f.close()

    data = data.replace(comment['raw'], newComment)

    f = open(comment['file'], 'wb')
    f.write(data)
    f.close()


if __name__ == '__main__':

    translate_client = translate.Client()
    x = texasRanger(ROOT)
    for X in x:
        comment = parser(X)
        patcher(comment)
        update(comment)
    
