#!/usr/bin/python3
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# TODO: verify these paths exist, print nice error if they don't
PLY_PATH = os.path.join(SCRIPT_DIR, "deps", "ply-3.11")
CPP_HEADER_PARSER_PATH = os.path.join(SCRIPT_DIR, "deps", "CppHeaderParser-2.7.4", "CppHeaderParser")

sys.path.insert(0, PLY_PATH)
sys.path.insert(0, CPP_HEADER_PARSER_PATH)

import CppHeaderParser

def parseHeader(header_filename):
    print("{}".format(header_filename))
    header = CppHeaderParser.CppHeader(header_filename)
    print("  {} includes:".format(len(header.includes)))
    for incl in header.includes:
        print("   {}".format(incl))
    print("  {} #defines:".format(len(header.defines)))
    for define in header.defines:
        print("   {}".format(define))
    print("  {} functions:".format(len(header.functions)))
    for func in header.functions:
        print("   {}".format(func["name"]))

def parseHeadersIn(dir, exclude):
    for entry_basename in os.listdir(dir):
        if entry_basename.endswith(".idl") or entry_basename.endswith(".mof"):
            continue
        if entry_basename in exclude:
            print("skipping '{}'".format(exclude))
            continue
        entry = os.path.join(dir, entry_basename)
        if os.path.isdir(entry):
            parseHeadersIn(entry, exclude)
        else:
            try:
                parseHeader(entry)
            except CppHeaderParser.CppParseError as e:
                print("PARSEERROR: {}".format(entry_basename))
            except RecursionError as re:
                print("PARSEERROR: {}".format(entry_basename))

def main():

    # just hardcode path to get started
    windows_include_path = "C:\\Program Files (x86)\\Windows Kits\\10\\Include\\10.0.17763.0"
    if not os.path.exists(windows_include_path):
        sys.exit("Error: windows sdk include path does not exist: {}".format(windows_include_path))

    #
    # Header Directories
    #
    # shared - seems to mostly be headers shared between user mode and kernel mode
    # um - user mode? the standard user mode windows headers (like windows.h)
    # km - kernel mode?
    # winrt - windows rt api (windows store)
    process_shared_headers = True
    process_user_mode_headers = True

    if process_shared_headers:
        shared_path = os.path.join(windows_include_path, "shared")
        if not os.path.exists(shared_path):
            sys.exit("Error: windows include dir is missing the 'shared' subdirectory: {}".format(shared_path))
        parseHeadersIn(shared_path, ["apdevpkey.h", "clfs.h", "devpkey.h", "devpropdef.h", "hidclass.h", "ifdef.h",
            "ksmedia.h", "ksproxy.h", "ktmtypes.h", "kxarm.h", "kxarmunw.h", "kxarm64.h", "kxarm64unw.h",
            "mstcpip.h", "netiodef.h", "nfpdev.h", "ntdddisk.h","ntddndis.h","ntddser.h","ntddstor.h", "ntddcdvd.h",
            "pciprop.h","poclass.h", "rpcdce.h", "scsi.h", "sensorsdef.h", "specstrings.h", "srb.h", "tdi.h", "TraceLoggingProvider.h",
            "winbio_types.h", "windot11.h", "winbio_ioct.h", "winsmcrd.h", "ws2def.h",
        ])

    if process_user_mode_headers:
        user_mode_path = os.path.join(windows_include_path, "um")
        if not os.path.exists(user_mode_path):
            sys.exit("Error: windows include dir is missing the 'um' subdirectory: {}".format(user_mode_path))
        parseHeadersIn(user_mode_path, ["advpub.h", "anchorsyncdeviceservice.h", "atlthunk.h",
            "Audioclient.h", "audioenginebaseapo.h","AudioEngineEndpoint.h","aviriff.h",
            "bridgedeviceservice.h","bthledef.h","calendardeviceservice.h","CallConv.Inc",
            "coguid.h","commdlg.h","contactdeviceservice.h","cper.h","cryptxml.h",
            "d2d1.h","d2d1_1.h","d3dcsx.h","dbdaoid.h","ddraw.h","devfiltertypes.h",
            "deviceservices.h","devquerydef.h","DirectXCollision.h","DirectXPackedVector.h",
            "DsGetDC.h","EapAuthenticatorActionDefine.h","eaptypes.h","ehstorextensions.h",
            "eventman.xsd","fullenumsyncdeviceservice.h","functiondiscoverykeys.h",
            "functiondiscoverykeys_devpkey.h","GLU.h","http.h",
            "icu.h","icucommon.h","icui18n.h","LMaccess.h","LMDFS.h","LMServer.h","lmstats.h",
            "medparam.h","memoryapi.h","messagedeviceservice.h","metadatadeviceservice.h",
            "mmdeviceapi.h","mmiscapi.h", "MspAddr.h",
        ])

    #windows_header = os.path.join(windows_include_path, "um", "windows.h")
    #parseHeader(windows_header)


main()
