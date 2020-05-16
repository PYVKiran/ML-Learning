from flask import Flask, render_template, request
from flask_cors import CORS, cross_origin
import urllib3
from pymongo import MongoClient
from bs4 import BeautifulSoup as bs

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
@cross_origin()
def home():
    if request.method == "GET":
        return render_template("home.html")
    else:
        rtrn_msg, rtrn_flg, search_string, rvws_data = home_post()
        if rtrn_flg:
            rvw_data = list(rvws_data)
            for ind_rvw in rvw_data:
                del ind_rvw["_id"]
                del ind_rvw["Product"]
            rvw_keys = rvw_data[0].keys()
            print("rtrn_msg", rtrn_msg)
            print("rtrn_flg", rtrn_flg)
            print("search_string", search_string)
            print("rvws_data", rvw_data)
            return render_template("review.html", rvw_rows=rvw_data, rvw_cols=rvw_keys, search_string=search_string)
        else:
            return rtrn_msg


def home_post():
    try:
        base_url = "https://www.flipkart.com"
        search_string = request.form["inp_srch_str"]
        search_string = search_string.replace(" ", "").upper()
        clctn = db_init()
        clctn, ver_prd_db = db_find(clctn, search_string)
        print("search_string", search_string)
        print("DB Rec count : ", ver_prd_db.count())
        if (ver_prd_db.count() == 0):
            search_url = base_url + "/search?q=" + search_string
            urllib_pool = urllib3.PoolManager()
            req_url = urllib_pool.request("GET", search_url)
            req_url_data = bs(req_url.data, "html.parser")
            req_url_data_tags = req_url_data.find_all("div", {"class": "bhgxx2 col-12-12"})
            del req_url_data_tags[0:2]
            req_trgt_item_href = req_url_data_tags[0].div.div.div.a["href"]
            req_trgt_item_url = base_url + req_trgt_item_href
            trgt_item = urllib_pool.request("GET", req_trgt_item_url)
            trgt_item_data = bs(trgt_item.data, "html.parser")
            trgt_item_data_tags = trgt_item_data.find_all("div", {"class": "_3nrCtb"})
            db_rec = []
            for product in trgt_item_data_tags:
                try:
                    product_rating = product.div.div.div.div.text
                except:
                    product_rating = "No Rating"
                try:
                    product_comment_hdr = product.div.div.div.p.text
                except:
                    product_comment_hdr = "No Comment Header"
                try:
                    product_comment_desc_tag = product.find("div", {"class": ""})
                    product_comment_desc = product_comment_desc_tag.div.text
                except:
                    product_comment_desc = "No Comment Description"
                try:
                    product_user_tag = product.find("p", {"class": "_3LYOAd _3sxSiS"})
                    product_user = product_user_tag.text
                except:
                    product_user = "No Username"

                if (product_user == "No Username" and product_comment_desc
                        == "No Comment Description" and product_comment_hdr == "No Comment Header" and product_rating == "No Rating"):
                    continue
                else:
                    db_rec_dict = {"Product": search_string, "Username": product_user, "Rating": product_rating,
                                   "Comment_Header": product_comment_hdr, "Comment_Description": product_comment_desc}
                    db_rec.append(db_rec_dict)

            if (len(db_rec) == 0):
                return "No Item matched", False, search_string, ver_prd_db
            else:
                clctn, insert_result = db_insertmany(clctn, db_rec)
                if insert_result.acknowledged:
                    clctn, ver_prd_db = db_find(clctn, search_string)
                    return "Reviews Inserted Sucessfully", True, search_string, ver_prd_db
                else:
                    print(db_rec)
                    return "Reviews Insertion Failed", False, search_string, ver_prd_db
        else:
            return "HAVE Values", True, search_string, ver_prd_db
    except Exception as e:
        raise Exception(str(e))


def db_init():
    dbClient = MongoClient("mongodb://127.0.0.1:27017/")
    db = dbClient["web_scrapper"]
    clctn = db["review_scrapper"]
    return clctn


def db_find(clctn, search_string):
    ver_prd_db = clctn.find({"Product": search_string})
    return clctn, ver_prd_db


def db_insertmany(clctn, db_rec):
    inserted_rec = clctn.insert_many(db_rec)
    return clctn, inserted_rec


app.run(debug=True)
