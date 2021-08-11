import xml.etree.ElementTree as ET
import re
from subprocess import Popen, PIPE
import readline

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    TYPE = '\u001b[34;1m'
    MNEMONIC = '\u001b[37m'

info_string = """\
\033[95m
/rm regex mnemonic search
/asm regex asm mnemonic search
/desc regex description search
/cat regex category search
/catid show category for result id
/tech regex search for tech
/techid show tech for result id
/id show description for result id
/cpuid show cpuid for result id
/op show operation for result id
/max change maximum number of results
/list re-list current result page
/c copy to clipboard
/exit quit
\033[0m
"""


def open_xml():
    tree = ET.parse('data-latest.xml')
    root = tree.getroot()
    return root

def match_blacklist(blacklist, name):
    if blacklist is not None:
        for i in blacklist:
            if re.match(".*" + i + ".*", name):
                return True
    return False

def search_intrin(root, mnemonic_key = None, asm_mnemonic_key = None, descr_key = None, tech_key = None, category_key = None, cpuid_blacklist = None, techid_blacklist = None):
    result = []
    for i,child in enumerate(root):
        mnemonic = child.attrib['name']
        tech = child.attrib['tech']
        cpuid = child.find('CPUID')
        
        asm_mnemonic = child.find('instruction')
        if asm_mnemonic is not None:
            asm_mnemonic = asm_mnemonic.attrib['name'].lower()
        
        if cpuid is not None:
            cpuid = cpuid.text
            if match_blacklist(cpuid_blacklist, cpuid) or match_blacklist(techid_blacklist, tech):
                continue
            
        category = child.find('category').text
        returns = child.find('return')
        return_type = None
        if returns is not None:
            return_type = returns.attrib['type']
        
        parameters = child.findall('parameter')
        parameters_list = []
        if parameters is not None:
            for i in parameters:
                parameters_list.append(i.attrib)
        
        descr = child.find('description').text
        operation = child.find('operation')
        if operation is not None:
            operation = operation.text
        
        tmp_result = {"mnemonic" : mnemonic, "asm_mnemonic" : asm_mnemonic, "tech" : tech, "cpuid" : cpuid, "category" : category, "return type" : return_type, "parameters" : parameters_list, "descr" : descr, "operation" : operation}
        
        if mnemonic_key is not None:
            if re.match(".*" + mnemonic_key + ".*", mnemonic):
                result.append(tmp_result)
        
        if asm_mnemonic_key is not None and asm_mnemonic is not None:
            if re.match(".*" + asm_mnemonic_key + ".*", asm_mnemonic):
                result.append(tmp_result)
        
        if descr_key is not None:
            if re.match(".*" + descr_key + ".*", descr):
                result.append(tmp_result)
        
        if tech_key is not None:
            if re.match(".*" + tech_key + ".*", tech):
                result.append(tmp_result)
        
        if category_key is not None:
            if re.match(".*" + category_key + ".*", category):
                result.append(tmp_result)
        
    return result

def generate_formatted_mnemonic(mnemonic):
    i = mnemonic
    padding = 8 - len(i['return type'])
    if padding < 0:
        padding = 0
    ret_type = f"{bcolors.TYPE}{i['return type']}{' ' * padding}{bcolors.ENDC}"
    mnemonic = f"{bcolors.MNEMONIC}{i['mnemonic']}{bcolors.ENDC}"
    parameters = ""
    for n,p in enumerate(i['parameters']):
        if p['type'] == 'void':
            parameters += f"{bcolors.TYPE}{p['type']}{bcolors.ENDC}"
            break
        if n == 0:
            parameters += f"{bcolors.TYPE}{p['type']}{bcolors.ENDC} {p['varname']}"
        else:
            parameters += f", {bcolors.TYPE}{p['type']}{bcolors.ENDC} {p['varname']}"
    
    msg = ret_type + mnemonic + '(' + parameters + ')'
    return msg

def search_wrapper(root, results, max_results, search_key, cpuid_blacklist, techid_blacklist):
    key = search_key.split()
    if len(key) == 1:
        if key[0] == "/help":
            print(info_string)
            return False
        elif key[0] == "/exit":
            exit()
        elif key[0] == "/list":
            return True
        else:               #default search
            mnemonic_key = re.escape(key[0])
            results[:] = search_intrin(root, mnemonic_key = mnemonic_key, cpuid_blacklist = cpuid_blacklist, techid_blacklist = techid_blacklist)
            
    elif key[0] == "/id":   #inspect result from last search
        id_no = int(key[1])
        if id_no < len(results):
            msg = "\n" + generate_formatted_mnemonic(results[id_no]) + "\n" + results[id_no]['descr'] + "\n"
            print(msg)
            return False
            
    elif key[0] == "/op":   #inspect result from last search
        id_no = int(key[1])
        if id_no < len(results):
            msg = "\n" + generate_formatted_mnemonic(results[id_no]) + "\n" + results[id_no]['operation']
            if results[id_no]['asm_mnemonic'] is not None:
                msg = msg + results[id_no]['asm_mnemonic']
            print(msg)
            return False
            
    elif key[0] == "/cpuid":
        id_no = int(key[1])
        if id_no < len(results):
            msg = "\n" + generate_formatted_mnemonic(results[id_no]) + "\n" + results[id_no]['cpuid']
            print(msg + "\n")
            return False
    
    elif key[0] == "/techid":   #inspect result from last search
        id_no = int(key[1])
        if id_no < len(results):
            msg = "\n" + generate_formatted_mnemonic(results[id_no]) + "\n" + results[id_no]['tech'] + "\n"
            print(msg)
            return False
    
    elif key[0] == "/catid":   #inspect result from last search
        id_no = int(key[1])
        if id_no < len(results):
            msg = "\n" + generate_formatted_mnemonic(results[id_no]) + "\n" + results[id_no]['category'] + "\n"
            print(msg)
            return False
    
    elif key[0] == "/c":   #copy to clipboard
        id_no = int(key[1])
        if id_no < len(results):
            #msg = "\n" + generate_formatted_mnemonic(results[id_no]) + "\n"
            
            mn = results[id_no]['mnemonic']
            p = Popen(['xsel','-bi'], stdin=PIPE)
            p.communicate(input=mn.encode())
            print("\ncopied to clipboard:", mn, "\n")
            return False
    
    elif key[0] == "/max":
        max_results[0] = int(key[1])
        
    elif key[0] == "/rm":   #regex mnemonic
        mnemonic_key = key[1]
        results[:] = search_intrin(root, mnemonic_key = mnemonic_key, cpuid_blacklist = cpuid_blacklist, techid_blacklist = techid_blacklist)
        
    elif key[0] == "/asm":   #regex asm mnemonic
        asm_mnemonic_key = key[1]
        results[:] = search_intrin(root, asm_mnemonic_key = asm_mnemonic_key, cpuid_blacklist = cpuid_blacklist, techid_blacklist = techid_blacklist)
        
    elif key[0] == "/desc": #descr search
        descr_key = key[1]
        results[:] = search_intrin(root, descr_key = descr_key, cpuid_blacklist = cpuid_blacklist, techid_blacklist = techid_blacklist)
    
    elif key[0] == "/tech":   #regex tech search
        tech_key = key[1]
        results[:] = search_intrin(root, tech_key = tech_key, cpuid_blacklist = cpuid_blacklist, techid_blacklist = techid_blacklist)
    
    elif key[0] == "/cat":   #regex category search
        category_key = key[1]
        results[:] = search_intrin(root, category_key = category_key, cpuid_blacklist = cpuid_blacklist, techid_blacklist = techid_blacklist)
    
    else:
        print("invalid search\n")
        return False
        
    return True


def complete(text,state):
    words = ["help", "exit", "list", "id", "op", "cpuid", "techid", "catid", "c", "max", "rm", "asm", "desc", "tech", "cat"]
    results = [x for x in words if x.startswith(text)] + [None]
    return results[state]


def main():
    readline.parse_and_bind("tab: complete")
    readline.set_completer(complete)
    root = open_xml()
    result = []
    max_results = [30]
    cpuid_blacklist = ['AVX512', 'KNCNI']
    techid_blacklist = ['SVML']
    print(info_string)
    while True:
        search_key = input("search: ")
        to_print = search_wrapper(root, result, max_results, search_key, cpuid_blacklist, techid_blacklist)
        if to_print:
            for j,i in enumerate(result[0:max_results[0]]):
                msg = generate_formatted_mnemonic(i)
                id_str = str(j) + ' '
                if len(id_str) < 3:
                    id_str = ' ' + id_str
                msg = id_str + msg
                print(msg)
            if(len(result) > max_results[0]):
                print("...")
            print("")
    





if __name__ == "__main__":
    main()
