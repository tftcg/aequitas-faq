import os
import glob
import re
from jinja2 import Template, Environment, FileSystemLoader
import xml.etree.ElementTree as ET 
import json
from collections import Counter
from collections import OrderedDict


# Global
TOP_OUTPUT_DIR ='docs'


# This also matches to FortMax urls
def safe_name(name):
    return name.lower().replace(' ', '-').replace('---', '-').replace("'", '').replace('?', '').replace('(','').replace(')', '').replace('&-', '').replace(',', '').replace('/-', '')

# {wave_code.lower}{type}/{name}-{wave_code}-{alt if character}
def build_image_path(pretty_path, tag_node):
    path=tag_node.attrib['wave_code'].lower() + '/'

    if 'Character' in pretty_path:
        path += 'character'
    elif 'Stratagems' in pretty_path:
        path += 'stratagem'
    elif 'Battle' in pretty_path:
        path += 'battle'
    else:
        print('Error: Unusual card found with wave code')

    path += '/' + safe_name(tag_node.attrib['name']) + '-' + tag_node.attrib['wave_code']

    if 'Character' in pretty_path:
        path += '-alt'

    return path

# Returns the inner xml of an Element; i.e. <a>Text <b>bob</b>. </a> would return 'Text <b>bob</b>. '
# https://stackoverflow.com/questions/3443831/python-and-elementtree-return-inner-xml-excluding-parent-element
def inner_xml(element):
    return (element.text or '') + ''.join(ET.tostring(e).decode() for e in element)

# Returns the text to output
def prepare_text(node, hyperlinks=None):
    text = inner_xml(node)
    newtext = text.replace('[[', '').replace(']]', '').strip()
    newtext = re.sub(r'(.)\n(.)', r'\1<br/>\2', newtext)
    newtext = newtext.replace('<tftcg-note>', '<div class="tftcg-note">').replace('</tftcg-note>', '</div>')
    newtext = newtext.replace('<tftcg-fan-content>', '<div class="tftcg-fan-content">').replace('</tftcg-fan-content>', '</div>')
    newtext = newtext.replace('<a href="http', '<a class="external" href="http')

    if(hyperlinks):
        for tag in hyperlinks:
            if(tag in newtext):
                newtext = re.sub(tag, '<a href="' + hyperlinks[tag] + '">' + tag + '</a>', newtext, 1)
            elif(' - ' in tag):
                chopped_tag = tag.split(' - ')[0]
                if(chopped_tag in newtext):
                    newtext = re.sub(chopped_tag, '<a href="' + hyperlinks[tag] + '">' + chopped_tag + '</a>', newtext, 1)
                else:
                    # Try removing common prefixes
                    chopped_tag = chopped_tag.replace('Captain ', '').replace('General ', '').replace('Major ', '').replace('Private ', '').replace('Raider ', '').replace('Sergeant ', '').replace('Specialist ', '')
                    if(chopped_tag in newtext):
                        newtext = re.sub(chopped_tag, '<a href="' + hyperlinks[tag] + '">' + chopped_tag + '</a>', newtext, 1)
            
    return newtext

# Returns nothing
def mkdirp(directory):
    # TODO: if os.path.isfile(directory)
    if( not os.path.isdir(directory) ):
        os.makedirs(directory)

# Returns WotC|Aequitas|Community
def source_label(source_name):
    if("Aequitas" in source_name):
        return 'Aequitas'
    elif("FAQ" in source_name or "Roundup" in source_name):
        return 'WotC'
    else:
        return 'Community'

# Returns number of entries found for the leaf page
def generate_leaf(tag_node, faq_db, output_dir, leaf_template, hyperlinker, parent_stack):
    filename = os.path.join(output_dir, safe_name(tag_node.attrib['name']) + ".html")
    pretty_path = re.sub('-', ' ', re.sub('/', ' / ', output_dir[len(TOP_OUTPUT_DIR)+1:]) ).title()
    leaf_name = tag_node.attrib['name']
    markup = '[[' + leaf_name + ']]'
    markup_required = False
    if('markup_required' in tag_node.attrib and tag_node.attrib['markup_required'].lower() == 'true'):
        markup_required = True

    found_entries = []    # contains array of name, source_url, faq node

    # Find FAQ entries for this leaf_name
    # Loop over every key, value in the faq_db
    for faqfile, node in faq_db.items():
        source_url = node.attrib['source_url']
        if('source' in node.attrib):
            source_name = node.attrib['source']
        else:
            source_name = node.attrib['name']
        for target_node in node.findall('./target'):
            for entry_node in target_node.findall('./entry'):
                found = False
                target_name = target_node.attrib['name']
                # Look for any <target> with a name that matches this tag
                if target_name == leaf_name:
                    found = True
                # Look for any entry that contains this tag
                elif 'tags' in entry_node.attrib and leaf_name in entry_node.attrib['tags'].split(','):
                    found = True
                # If it's allowed, search for the tag in the text
                elif not markup_required and leaf_name in ET.tostring(entry_node, method='text').decode():
                    found = True
                # Search for [[tag]] in the text
                elif markup in ET.tostring(entry_node, method='text').decode():
                    found = True

                if(found):
                    # Identify hyperlinks
                    hyperlinks = {}

                    if(target_name != leaf_name and target_name in hyperlinker[0]):
                        hyperlinks[target_name] = hyperlinker[0][target_name]

                    if 'tags' in entry_node.attrib:
                        for tag in entry_node.attrib['tags'].split(','):
                            if(tag != leaf_name and tag in hyperlinker[0]):
                                hyperlinks[tag] = hyperlinker[0][tag]

                    # Loop over every other tag that is not markup_required and see if it shows up in the text
                    for tag in hyperlinker[1]:
                        if(tag != leaf_name and tag in ET.tostring(entry_node, method='text').decode() and tag in hyperlinker[0]):
                            hyperlinks[tag] = hyperlinker[0][tag]

                    # TODO: Do [[]] tags; or just remove that feature

                    found_entries.append( [source_name, source_url, entry_node, faqfile, hyperlinks] )

    if(len(found_entries) != 0):
        page = leaf_template.render(f_safe_name=safe_name, f_prepare_text=prepare_text, entries=found_entries, faq_name=leaf_name, f_source_label=source_label, parent_stack=parent_stack, tag_node=tag_node, filename=filename[len(TOP_OUTPUT_DIR)+1:], pretty_path=pretty_path, f_build_image_path=build_image_path, faq_db=faq_db )

        f = open(filename, "w")
        f.write(page)
        f.close()

        # then generate an xml version
        xmlname = re.sub(r'.html', '.xml', filename)
        f = open(xmlname, 'w')
        escaped_leaf_name = re.sub(r' & ', ' &amp; ', leaf_name)
        f.write('<faq><target name="' + escaped_leaf_name + '">')
        for entry in found_entries:
            # [source_name, source_url, entry_node, faqfile, hyperlinks]
            txt = ET.tostring(entry[2], encoding="unicode")
            txt = re.sub(r'<entry ', '<entry source="' + entry[0] + '" ', txt)
            f.write(re.sub(r' & ', ' &amp; ', txt))

        f.write("</target></faq>")
        f.close()

    return len(found_entries)

# Returns nothing
def generate_branch(node, faq_db, output_dir, tag_blocks, category_blocks, branch_template, parent_stack):
    filename = os.path.join(output_dir, 'index.html')

    page=branch_template.render(f_safe_name=safe_name, tag_blocks=tag_blocks, category_blocks=category_blocks, parent_stack=parent_stack, this_node=node, filename=filename[len(TOP_OUTPUT_DIR)+1:])

    f = open(filename, "w")
    f.write(page)
    f.close()

# Returns: [Number items found, tag:file dictionary, tag:count dictionary]
def walk_branch(node, faq_db, output_dir, leaf_template, branch_template, hyperlinker, parent_stack=[]):

    tag_blocks = []
    category_blocks = []
    total_found = 0
    found_tags = {}   # Used to build the json_index
    found_count = {}  # Used to make top tens etc

    mkdirp(output_dir)

    for tag_node in node.findall('./tag'):
        parent_stack.append(node)
        found = generate_leaf(tag_node, faq_db, output_dir, leaf_template, hyperlinker, parent_stack)
        parent_stack.pop()
        if(found > 0):
            tag_blocks.append([tag_node, found])
            total_found += found
            found_tags[tag_node.attrib['name']] = (output_dir + "/" + safe_name(tag_node.attrib['name']) + ".html").replace(TOP_OUTPUT_DIR, '')
            found_count[tag_node.attrib['name']] = found

    for category_node in node.findall('./category'):
        subdir = os.path.join(output_dir, safe_name(category_node.attrib['name']))
        parent_stack.append(node)
        found_data = walk_branch(category_node, faq_db, subdir, leaf_template, branch_template, hyperlinker, parent_stack)
        parent_stack.pop()
        if(found_data[0] > 0):
            category_blocks.append([category_node, found_data[0]])
            total_found += found_data[0]
            found_tags.update(found_data[1])
            found_count.update(found_data[2])

    generate_branch(node, faq_db, output_dir, tag_blocks, category_blocks, branch_template, parent_stack)

    return [total_found, found_tags, found_count]

# Load Leaf Template
leaf_template_file = open('templates/leaf.jinja2','r')
leaf_template_text = leaf_template_file.read()
leaf_template = Environment(loader=FileSystemLoader("templates/")).from_string(leaf_template_text)

# Load Branch Template
branch_template_file = open('templates/branch.jinja2','r')
branch_template_text = branch_template_file.read()
branch_template = Environment(loader=FileSystemLoader("templates/")).from_string(branch_template_text)

# Load the taglist.xml file
taglist_tree = ET.parse('taglist.xml')
taglist_node=taglist_tree.getroot()

def load_faqs_to_dict(faq_dir, faq_dict):
    faq_glob = os.path.join(faq_dir, '**', '*.xml')
    # Load all the FAQ XML files
    for file in glob.glob(faq_glob, recursive=True):
        filename = os.path.splitext(file)[0][len(faq_dir)+1:]
        faq_tree = ET.parse(file)
        faq_node=faq_tree.getroot()
        faq_db[filename] = faq_node

faq_db = OrderedDict()
load_faqs_to_dict('faqxml-official', faq_db)
load_faqs_to_dict('faqxml-roundups', faq_db)
load_faqs_to_dict('faqxml-unofficial', faq_db)

# Load the previous json index for use in hyperlinking
faq_index_filename = os.path.join(TOP_OUTPUT_DIR, "faqindex.json")
if(os.path.exists(faq_index_filename)):
    with open(faq_index_filename) as json_file:
        search_index = json.load(json_file)
else:
    search_index = {}

# Walk the taglist and build the automarkup tags for use in hyperlinking
automarkup_tags = []
for tag in taglist_node.findall('.//tag'):
    if('markup_required' not in tag.attrib):
        automarkup_tags.append(tag.attrib['name'])

hyperlinker = [search_index, automarkup_tags]

# Walk the taglist and generate pages
found_data = walk_branch(taglist_node, faq_db, TOP_OUTPUT_DIR, leaf_template, branch_template, hyperlinker)

# Generate json index
f = open(faq_index_filename, "w")
f.write(json.dumps(found_data[1]))
f.close()

# Generate top N page
# Load TopN Template
topn_template_file = open('templates/topn.jinja2','r')
topn_template_text = topn_template_file.read()
topn_template = Environment(loader=FileSystemLoader("templates/")).from_string(topn_template_text)

# HACK: Finding the tags that are cards. This is a bit of a cheap hack based on url habits.
found_characters = {k:found_data[2][k] for k in found_data[2] if re.search('/characters/', found_data[1][k])}
counted_characters = Counter(found_characters)
page = topn_template.render(title="Top Twenty Most FAQ'd Character Cards", url_dictionary=found_data[1], counted_dictionary=counted_characters.most_common(20), filename='top-characters.html')
f = open(os.path.join(TOP_OUTPUT_DIR, 'top-characters.html'), "w")
f.write(page)
f.close()

found_battle_cards = {k:found_data[2][k] for k in found_data[2] if re.search('/battle-cards/', found_data[1][k])}
counted_battle_cards = Counter(found_battle_cards)
page = topn_template.render(title="Top Twenty Most FAQ'd Battle Cards", url_dictionary=found_data[1], counted_dictionary=counted_battle_cards.most_common(20), filename='top-battle-cards.html')

f = open(os.path.join(TOP_OUTPUT_DIR, 'top-battle-cards.html'), "w")
f.write(page)
f.close()
