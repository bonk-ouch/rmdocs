# -*- coding: utf-8 -*-
"""
Created on Mon Oct  5 20:51:09 2026

@author: Thomas
"""

import json
import xml.etree.ElementTree as ET
import sys
from importlib.resources import files

def left_associative(operator):
    return True if operator in "+-*/" else False

def apply_operator(opstack,out):
    op = opstack.pop()
    result = None
    if op == "+":
        result = out.pop(-2) + out.pop(-1)

    elif op == "-":
        result = out.pop(-2) - out.pop(-1)

    elif op == "*":
        result = out.pop(-2) * out.pop(-1)

    elif op == "/":
        result = out.pop(-2) / out.pop(-1)

    elif op == "^":
        result = out.pop(-2) ** out.pop(-1)

    elif op == "<":
        result = out.pop(-2) < out.pop(-1)

    elif op == ">":
        result = out.pop(-2) > out.pop(-1)

    elif op == "||":
        left = out.pop(-2)
        right = out.pop(-1)
        result = left or right

    elif op == "&&":
        left = out.pop(-2)
        right = out.pop(-1)
        result = left and right

    elif op == ":":
        condition = out.pop(-3) > 0
        iftrue = out.pop(-2)
        iffalse = out.pop(-1)
        result = iftrue if condition else iffalse
        opstack.pop() #Remove the ? marker

    elif op == "?":
        pass # don't do anything here, wait for ":"


    if result != None:
        out.append(result)

def precedence(token,topoperator):
    prec = {
        "^":3,
        "*":2,
        "/":2,
        "+":1,
        "-":1,
        ">":-1,
        "<":-1,
        "||":-2,
        "&&":-2,
        "?":-3,
        ":":-3,
        "(":-100 # "(" must always be the lowest precedence and by itself
        }

    sameprec = prec[token] == prec[topoperator]
    lowerprec = prec[token] < prec[topoperator]

    return lowerprec or (sameprec and left_associative(token))

def isnumber(string):
    try:
        float(string)
        result = True
    except:
        result = False

    return result

def eval_expr(expression,variables):
    out = []
    opstack = []
    expression = str(expression)
    expression = expression.replace("(","( ")
    expression = expression.replace(")"," )")

    for token in expression.split():
        if isnumber(token):
            out.append(float(token))

        elif token == "(":
            opstack.append(token)

        elif token == ")":
            while opstack and opstack[-1] != "(":
                apply_operator(opstack,out)
            opstack.pop() # this should be the opening parenthesis (

        elif token in "+-*/^<>?:||&&": # is operator
            while opstack and precedence(token,opstack[-1]):
                apply_operator(opstack,out)
            opstack.append(token)

        else: #variable
            if token[0] == "-": # a token like "-variable"
                out.append(-1*variables[token[1:]])
            else:
                out.append(variables[token])

    while opstack:
        apply_operator(opstack,out)

    return float(out.pop())

def calc_consts(inputjson,constants):
    for line in inputjson:
        name, expression = next(iter(line.items()))
        constants[name] = eval_expr(expression,constants)
    return constants

def conv_svg_path(pathdata,consts):
    out = ""
    for token in map(str,pathdata):
        if token in "MLZC":
            out += token
        else:
            out += str(eval_expr(token,consts))

        out += " "
    return out

def recurseme(jsonitem,xmlparent,parentbb,id_list,var):
    var["parentWidth"] = parentbb[0]
    var["parentHeight"] = parentbb[1]
    element_id = "-".join(map(str,id_list))
    if jsonitem["type"] == "group":
        defs = ET.SubElement(xmlparent,"defs")

        root = ET.SubElement(defs,"g",{"id":element_id})

        x = eval_expr(jsonitem["boundingBox"]["x"],var)
        y = eval_expr(jsonitem["boundingBox"]["y"],var)
        width = eval_expr(jsonitem["boundingBox"]["width"],var)
        height = eval_expr(jsonitem["boundingBox"]["height"],var)

        for i,nextitem in enumerate(jsonitem["children"]):
            recurseme(nextitem,root,(width,height),id_list+[i,],var)


        if "repeat" in jsonitem.keys():
            if "columns" in jsonitem["repeat"].keys():
                xrep = jsonitem["repeat"]["columns"]
                if xrep == "infinite":
                    xposcond = parentbb[0]
                    xnegcond = 0
                elif xrep == "right":
                    xposcond = parentbb[0]
                    xnegcond = x
                elif xrep == "left":
                    xposcond = x
                    xnegcond = 0
                else:
                    xposcond = (eval_expr(xrep,var)-1)*width + x
                    xnegcond = x
            else:
                xposcond = x
                xnegcond = x


            if "rows" in jsonitem["repeat"].keys():
                yrep = jsonitem["repeat"]["rows"]
                if yrep == "infinite":
                    yposcond = parentbb[1]
                    ynegcond = 0
                elif yrep == "down":
                    yposcond = parentbb[1]
                    ynegcond = y
                elif yrep == "up":
                    yposcond = y
                    ynegcond = 0
                else:
                    yposcond = (eval_expr(yrep,var)-1)*height + y
                    ynegcond = y

            else:
                yposcond = y
                ynegcond = y

            #go in postive x direction
            xnew = x
            while xnew <= xposcond:
                #positive y direction
                ynew = y
                while ynew <= yposcond:
                    ET.SubElement(xmlparent,"use",{"href":"#"+element_id,"x":str(xnew),"y":str(ynew)})
                    ynew += height

                #negative y direction
                ynew = y
                while ynew > ynegcond:
                    ET.SubElement(xmlparent,"use",{"href":"#"+element_id,"x":str(xnew),"y":str(ynew)})
                    ynew -= height

                xnew += width

            xnew = x
            while xnew > xnegcond:
                ynew = y
                while ynew < yposcond:
                    ET.SubElement(xmlparent,"use",{"href":"#"+element_id,"x":str(xnew),"y":str(ynew)})
                    ynew += height

                ynew = y
                while ynew > ynegcond:
                    ET.SubElement(xmlparent,"use",{"href":"#"+element_id,"x":str(xnew),"y":str(ynew)})
                    ynew -= height
                xnew -= width


        else: # No repeat element. Just place it once
            ET.SubElement(xmlparent,"use",{"href":"#"+element_id,"x":str(x),"y":str(y)})


    elif jsonitem["type"] == "path":
        if "fillColor" in jsonitem.keys():
            fill = jsonitem["fillColor"]
        else:
            fill = "none"

        if "strokeColor" in jsonitem.keys():
            stroke = jsonitem["strokeColor"]
        else:
            stroke = "black"

        ET.SubElement(xmlparent,"path",{"d":conv_svg_path(jsonitem["data"],var),"stroke":stroke,"fill":fill,"id":element_id})


    elif jsonitem["type"] == "text":
        text = jsonitem["text"]
        fontsize = eval_expr(jsonitem["fontSize"],var)
        #Textsize is a variable used in text elements
        #This is an rough estimate of textwidth that works fine so far
        var["textWidth"] = 0.5*fontsize*len(text)
        x = str(eval_expr(jsonitem["position"]["x"],var))
        y = str(eval_expr(jsonitem["position"]["y"],var))

        textel = ET.SubElement(xmlparent,"text",{"x":x,"y":y,"font-size":str(fontsize),"id":element_id})
        textel.text = text

def create_svg(jsonobject,width_px,height_px):
    constants = {"templateWidth":1404,
                 "templateHeight":1872,
                 "paperOriginX":0}

    var = calc_consts(jsonobject["constants"],constants)

    template = ET.Element('g',{"id":"template"})
    for i,item in enumerate(jsonobject["items"]):
        recurseme(item,template,(width_px,height_px),[i,],var)



    return template #str(ET.tostring(template,encoding="utf-8"))

def runme(templatename,width,height):
    template_file = files("rmdocs").joinpath("templatefiles", f"{templatename}.template")
    with template_file.open("r",encoding="utf-8") as file:
        data = json.load(file)

    return create_svg(data,width,height)


if __name__ == "__main__":
    with open(sys.argv[1], "r") as file:
        data = json.load(file)

    tree = create_svg(data)

    tree.write(sys.argv[2], encoding="utf-8", xml_declaration=True)


