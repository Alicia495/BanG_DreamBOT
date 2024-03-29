from email.errors import InvalidMultipartContentTransferEncodingDefect
import os
import tweepy
import urllib.request
import urllib.error
import json
from collections import OrderedDict
import datetime
import re
import key
import shutil
import AI_vision
import time
import glob
from tqdm import tqdm

os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true' #GPUメモリを必要分しか確保しない設定

BearerToken = key.BearerToken
access_token = key.access_token
access_token_secret = key.access_token_secret
consumer_key = key.consumer_key
consumer_secret = key.consumer_secret

DIR = "D:\バンドリ関連\画像\Twitter" #画像を保存するとこ
OUT_DIR = "D:\バンドリ関連\画像\OUT"
JSON_DIR = "tweetData.json"#ツイートデータを保存するとこ
MY_ID = {1447221621874315265,1073602536224030721,1373311376119132162}#管理ユーザーID
rejectHashTags = ["ガルパ履歴書","バンドリ履歴書","バンドリーマーさんと仲良くなりたい","ラーメン","柴犬","コスプレ"]
rejectTweetWord = ["コスプレ","柴犬","ラーメン","おは","cosplay","Cosplay"]
rejectRetweetRatio = 0.05 #はじくリツイートとふぁぼの比率

#----------------------------------------------------------------------
auth = tweepy.OAuthHandler(consumer_key, consumer_secret) #認証を通すとこ
auth.set_access_token(access_token, access_token_secret)

api = tweepy.API(auth,wait_on_rate_limit = True)
#-------------------------------------------------------------------------

def getTweet():
    public_tweets = api.home_timeline()
    for tweet in public_tweets:
        print(tweet.text)

def tweet(tweet_text):
    api.update_status(tweet_text)

oldurl = None

def downloadImg(url, dir):
    global oldurl
    if url != oldurl:
        try:
            with urllib.request.urlopen(url) as web_file:
                data = web_file.read()
                with open(dir, mode='wb') as local_file:
                     local_file.write(data)
                     oldurl = url
        except urllib.error.URLError as e:
            print(e)
    
def download_file_to_dir(url, dst_dir):
    downloadImg(url, os.path.join(dst_dir, os.path.basename(url)))

def getImage(tweet):

            try:
                url=tweet.extended_entities['media'][0]['media_url']
                print(url + "を保存しました")
                download_file_to_dir(url,DIR)
                url=tweet.extended_entities['media'][1]['media_url']
                print(url+ "を保存しました")
                download_file_to_dir(url,DIR)
                url=tweet.extended_entities['media'][2]['media_url']
                print(url+ "を保存しました")
                download_file_to_dir(url,DIR)
                url=tweet.extended_entities['media'][3]['media_url']
                print(url+ "を保存しました")
                download_file_to_dir(url,DIR)
            except:
                pass #画像がないときはなにもしない

def getKeyFromValue(d, val):
    keys = [k for k, v in d.items() if v == val]
    if keys:
        return keys[0]
    return None

def retweet(word,FAV_CNT,searchCNT):#15分当たり450回検索可
    today = int(datetime.datetime.timestamp(datetime.datetime.now())) 
    print(word + "でふぁぼ数"+ str(FAV_CNT) +"サーチ開始")
    tweetList = {}
    wordList = inputJson()

    if word not in wordList: #入力されたwordキーがなければ新たに作成
         wordList[word] = {}
    tweetList = wordList[word]#指定されたwordキーをリストに展開


    if (today - int(wordList['lastSearchDate'])) > (6*60*60):#半日すぎたら
        print("IDをクリーンアップします")
        wordList['lastSearchDate'] = today
        for tweetWord in list(wordList["data"].keys()): #半日以上前のツイートIDを削除
            for tweetKey in list(wordList[tweetWord].keys()):
                 if (today - int (wordList[tweetWord][tweetKey])) > (6*60*60):
                     del wordList[tweetWord][tweetKey]
                     

    olderTweetId = min(tweetList,key = tweetList.get,default = None) #今まで検索したりツイートの中で最も古いツイートIDを取得

    #------------------------------------------------------------------------------------------------------------------------------------------
    for tweet in api.search_tweets(q = word,result_type = 'recent',max_id = olderTweetId,count = 100):
            try:
                tweetId = tweet.id #tweetID取得
                tweetDate = dateScale(str(tweet.created_at))#ツイート日取得 YYYY,MM,DD,HH,mm,SS
                tweetList[tweetId] = tweetDate
                url = tweet.extended_entities['media'][0]['media_url']#画像が含まれてるかの検証　なければ例外に飛ぶ
                fav = tweet.favorite_count#ふぁぼ数取得
             
                if str(tweetId) not in tweetList:
                    if (fav >= FAV_CNT):
                        if(advancedTweetCheck(tweet) == "pass"):#ふぁぼが指定数以上で&これまでにリツイートしてい&内容が悪くなかったらリツイート
                             print("tetweet charenge")
                             try:
                                api.create_favorite(tweetId)
                                api.retweet(tweetId)
                                print("ついーとID" + str(tweetId) +"をリツイート")
                                getImage(tweet)
                             except:
                                 print ("りつーとに失敗しました")
                                 pass
                        #else:
                            #print("tweet rejected")
                    #else:
                        #print("tweet rejected")
            
            except:
                pass

    wordList[word].update(tweetList)
    outputJson(wordList)

def checkImage(tweet):#AIによる画像のイラスト判定
    shutil.rmtree("image_temp")
    os.mkdir("image_temp")

    url=tweet.extended_entities['media'][0]['media_url']
    download_file_to_dir(url,"image_temp")

    imagePath_list = glob.glob('image_temp/*.jpg')
    for image_path in imagePath_list:
        image_type = AI_vision.AI_judge(image_path)
        print(image_type)
        if(image_type == "Negative"):
            shutil.move(image_path,OUT_DIR)
            return("out")
        else:
            return("pass")

def advancedTweetCheck(tweet):#その名の通りアドバンスなツイートのチェック　ハッシュタグやツイートの内容から不適切なものを判別する
    text = tweet.text
    hashTag = []
    for count in tweet.entities["hashtags"]:
        hashTag.append(count["text"])

    for rejectWord in rejectTweetWord: 
        if re.search(rejectWord,text) != None:
            return "out"

    for rejectTag in rejectHashTags:
        if rejectTag in hashTag:
            return "out"

    if checkRetweetVal(tweet) == "out":
        return "out"
    
    if checkImage(tweet) == "out":
        return "out"
       

    return "pass"

def checkRetweetVal(tweet):
    fav = tweet.favorite_count
    ret = tweet.retweet_count
    if(ret / fav) >= rejectRetweetRatio:
        return "pass"
    else :
        return "out"

def dateScale(rawDate):
    newDate = rawDate[:19]
    newDate = datetime.datetime.timestamp(datetime.datetime.strptime(newDate, '%Y-%m-%d %H:%M:%S'))#取得した日付をエポック秒に変換
    return int(newDate)

def inputData(word,FAV_CNT):#新たな検索ワードの追加
    jsonData = inputJson()
    searchData = {}
    searchData = jsonData['data']

    if word not in searchData:
        searchData[word] = int(FAV_CNT)
        jsonData['data'].update(searchData)

    outputJson(jsonData)

    retweet(word,FAV_CNT,100)

def inputJson():
    jsonData = {}
    with open(JSON_DIR,'r',encoding = 'shift_jis') as f:
        jsonData = json.load(f)
    f.close()
    return jsonData

def outputJson(data):
    with open(JSON_DIR,'w',encoding = 'shift_jis') as f:
        json.dump(data,f,indent = 2,ensure_ascii = False)
    f.close()

def AllResearch():
    jsonData = {}
    jsonData = inputJson()
    wordValue = len(jsonData['data'])
    wordCnt = 450 / wordValue
    for word in jsonData['data'].keys():
        retweet(word,jsonData['data'][word],int(wordCnt))
    print("レート待機中...")

def checkMentions():#15秒ずつ更新するとよき
    jsonData = {}
    idList = {}
    jsonData = inputJson()
    newerCheckedId = None
    try:
        idList = jsonData["checkedMentionsId"]
        newerCheckedId = max(idList,key = idList.get,default = None) #今まで検索したりメンションの中で最も新しいツイートIDを取得
    except:
        idList = {}


    for tweet in tweepy.Cursor(api.mentions_timeline,since_id = newerCheckedId).items(1):
        tweetId = tweet.id
        try:
            api.create_favorite(tweetId)
        except:
            pass

        if tweet.user.id in MY_ID:
            pass
        else:
            replyText = "@"+str(tweet.user.screen_name)+" "+"メンションありがとうございます！　現在、特定のユーザーに対してのみ操作を受け付けております。要望は開発者までお問い合わせください"
            try:
                api.update_status(status = replyText,in_reply_to_status_id = tweetId)
            except:
                pass
            return

        idList[tweetId] = dateScale(str(tweet.created_at))
        jsonData["checkedMentionsId"].update(idList)
        outputJson(jsonData)
        inputCmd(tweet)
        

    


    return

def inputCmd(tweet):#コマンドの処理部
    p = re.compile('[\u2E80-\u2FDF\u3005-\u3007\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\U00020000-\U0002EBEF\u30A1-\u30FF\u3041-\u309F0-9]+')#日本語と数字を抽出
    data = p.findall(tweet.text)
    
    
    try:
        cmd = data[0]
    except:
        try:
            replyText = "@"+str(tweet.user.screen_name)+" "+"不正な引数です。内容を確認してください"
            api.update_status(status = replyText,in_reply_to_status_id = tweet.id)
        except:
            pass
        return
    
    if cmd == "追加":

        try:
            word = str(data[1])
            if not re.fullmatch("\d+",data[2]) :
                raise
            fav = str(data[2])
            inputData(word,fav)
            replyText = "@"+str(tweet.user.screen_name)+" "+"検索リストに" + word + "をしきい値" + fav +"で追加しました" 
            api.update_status(status = replyText,in_reply_to_status_id = tweet.id)
        except:
            replyText = "@"+str(tweet.user.screen_name)+" "+"不正な引数です。内容を確認してください"
            api.update_status(status = replyText,in_reply_to_status_id = tweet.id)
            return

    if cmd == "更新":
        AllResearch()
        try:
            replyText = "@"+str(tweet.user.screen_name)+" "+"更新を開始しました" 
            api.update_status(status = replyText,in_reply_to_status_id = tweet.id)
        except:
            pass

    if cmd == "リスト":
        jsonData = {}
        jsonData = inputJson()
        reply = "@"+str(tweet.user.screen_name)+" "+"検索リストの中身は\n"
        for word in jsonData["data"]:
            reply += "「" + word + "」"
        reply += "です"
        try:
            api.update_status(status = reply,in_reply_to_status_id = tweet.id)
        except:
            pass
    if cmd == "履歴":
        try:
            jsonData = {}
            jsonData = inputJson()
            word = str(data[1])
            if word in jsonData["data"]:
                reply = "@"+str(tweet.user.screen_name)+" "+ "現在「" + word +  "」で検索しているツイートの日付は" + str(checkOlderSearchedTweetDate(word)) + "で検索済みのツイート数は" +  str(checkSearchedTweetValue(word)) + "です。"
            else:
                reply = "@"+str(tweet.user.screen_name)+" "+ "入力された検索ワードは現在登録されていません。コマンド「リスト」で登録されてる検索ワードを表示するか、コマンド「追加」でワードを追加して下さい。"
            
            api.update_status(status = reply,in_reply_to_status_id = tweet.id)
        except:
            replyText = "@"+str(tweet.user.screen_name)+" "+"不正な引数です。内容を確認してください"
            api.update_status(status = replyText,in_reply_to_status_id = tweet.id)
            return
            
    return


def checkOlderSearchedTweetDate(word):
    jsonData = {}
    jsonData = inputJson()
    val = min(jsonData[word].values())
    return datetime.datetime.fromtimestamp(val)
    
def checkSearchedTweetValue(word):
      jsonData = {}
      jsonData = inputJson()
      return len(jsonData[word])



def main():
    print("起動")
    
    count = 0
    bar = tqdm(total = 300,unit = "roop",unit_scale = True, ncols=70)
    bar.set_description('次の検索開始まで…')
    while True:
        bar.update(0.1)

        if (count % 150) == 0:
            checkMentions()
        if(count % 3000) == 0:
            AllResearch()
            bar.reset()

        count += 1

        if count >= 9000 :
            count = 0
        time.sleep(0.1)
    

if __name__ == "__main__":
    main()
   