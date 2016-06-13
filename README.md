# 仕様(仮)

## 概要

### 処理の流れ

1. 設定ファイル(`chiffon_client.conf`)の読み込み
2. スクリプトの引数で指定した`user_id`を基にCHIFFONサーバから`session_id`,`recipe_id`を取得
3. 画像,特徴量を保存するディレクトリを作成
4. TableObjectManagerを起動
5. TableObjectManagerによって保存された画像を随時チェック
6. 5.で検知された画像を256*256にサイズ変更
7. 6.で編集した画像を特徴抽出用プログラムに渡し、特徴量を取得,保存
8. 7.で得た特徴量をserver4recog(認識用プログラム)にHTTPで送信し認識結果を取得
9. 8.で得た認識結果をHTTPでCHIFFONに送信する

### 関連ファイル

* chiffon_client.py
   * 一連の処理を行うPythonスクリプトファイル
* chiffon_client.conf
   * 各種設定を記述したconfファイル
* logging.conf
   * ログ出力設定を記述したファイル。chiffon_client.confと同じディレクトリに置く必要がある。
* s4r_convtable.csv
   * server4recogの認識結果を対応する語彙セットに変換するためのテーブル(csv形式)
* lib/
   * chiffon_client.pyで用いるライブラリを置くディレクトリ

### インストール

pip でいくつかのパッケージを追加でインストールする。
```
pip install watchdog
pip install requests
```

### 引数

スクリプトは以下の様に引数を指定して起動する。

```
python chiffon_cient.py chiffon_cient.conf user_id grouptag [grouptag ...]
```

指定する引数は以下の通り。

* chiffon_cient.conf
  * chiffon_cient.confのパス
* user_id
   * ユーザー名
* grouptag
   * server4recogへ渡すサンプルに付加するグループタグ
   * 複数指定可能
     * 但し最低1つは必要

#### 例

```
python chiffon_cient.py C:\ChiffonClient\etc\chiffon_cient.conf chiffon image_feature_extractor_v1
```

### 終了方法

コンソール上で Ctrl-C を送ると停止します。
スクリプトの停止に合わせて Table Object Manager も停止します。

### 設定ファイルの記述

```
[chiffon_client]
# chiffon_clientが利用する全保存先ディレクトリのroot
output_root=C:\ChiffonClient\var\output

[table_object_manager]
# TableObjectManagerの絶対パス
path_exec=C:\ChiffonClient\bin\TableObjectManager.exe
# TableObjectManager実行時に渡すオプション引数
default_options=-d 0 --gpu_device 0 -v false
# mp4ファイルを入力とする場合の例:
# default_options=-d 0 --gpu_device 0 -v false --input C:\ChiffonClient\TableObjectManager\camA.mp4
# TableObjectManagerによる出力ファイルのディレクトリ
output_rawimage=table_object_manager\raw
output_touch=table_object_manager\PUT
output_release=table_object_manager\TAKEN
output_log=table_object_manager\table_object_manager.log
# 作業領域認識用マスク画像のパス（仕様についてはREADME.mdの「workspace_end_filenameの仕様」に記載）
workspace_end_filename=
# workspace_end_filename=C:\ChiffonClient\etc\workspace_end_cameraA.png
# 画像拡張子一覧
fileexts=.jpg,.png,.gif,.bmp,.tif

[object_region_box_extractor]
path_exec=C:\ChiffonClient\bin\ExtractObjectBoxRegion.exe
output_touch=object_region_box_extractor\PUT
output_release=object_region_box_extractor\TAKEN
default_options= --min_width 128

[image_feature_extractor]
# 特徴抽出プログラムの絶対パス
path_exec=C:\ChiffonClient\bin\sample_Mat2VecCNN.exe
# 特徴抽出プログラムを実行する際に移動するディレクトリ
working_dir=C:\ChiffonClient\bin\
# 特徴抽出プログラム実行時に渡すオプション引数
default_options=-s 256:256 -p C:\ChiffonClient\bin\sample_data\imagenet_val.prototxt -m C:\ChiffonClient\bin\sample_data\bvlc_reference_rcnn_ilsvrc13.caffemodel
# 特徴抽出プログラムによる出力ファイルディレクトリ
output_touch=image_feature_extractor\touch
output_release=image_feature_extractor\release
# 拡張子
fileext=.csv
# 抽出する特徴量の種類の名前
feature_name=ilsvrc13
default_group=image_feature_extractor_v1

[serv4recog]
host=kusk.mm.media.kyoto-u.ac.jp
port=80
path=/s4r/ml/kusk_object/ilsvrc13_128/svc/predict
# 結果保存用ディレクトリ
output_touch=serv4recog\touch
output_release=serv4recog\release
# 拡張子
logfileext=.log
fileext=.json
# objectid変換テーブル(csvファイル)の絶対パス
path_convtable=C:\ChiffonClient\ChiffonClient\src\s4r_convtable.csv

[chiffon_server]
host=chiffon.mm.media.kyoto-u.ac.jp
path_sessionid=/woz/session_id/
path_recipe=/woz/recipe/
path_receiver=/receiver
port=80
navigator=object_access
timestamp=%Y.%m.%d_%H.%M.%S.%f
# 結果保存用ディレクトリ
output_touch=chiffon_server\touch
output_release=chiffon_server\release
# 拡張子
logfileext=.log
fileext=.json

[product_env]
# Cygwin 環境下で Cygpath を使用する場合、1 にする。
use_cygpath=0
# table_object_manager を利用する場合、1 にする。
enable_table_object_manager=1
# image_feature_extractor を利用する場合、1 にする。
enable_image_feature_extractor=1
# Server4recog を利用する場合、1 にする。
enable_server4recog=1
```



## CHIFFONからの情報の取得

スクリプト起動時に引数で指定した`user_id`を基にCHIFFONから`session_id`,`recipe_id`を取得する。

* `session_id`
   * 書式:`{user_id}-{datetime}`
     * `user_id`:ユーザー名
        * スクリプト起動時の引数で指定する
     * `datetime`:ログイン日時
        * 書式:`yyyy.MM.dd_HH.MM.ss.ffffff`
           * 例:`guest-2015.12.08_14.33.56.381162`
   * `http://{chiffon_server["host"]}:{chiffon_server["port"]}/woz/session_id/{user_id}`から取得可能
     * 取得できる`session_id`は複数で、上の方ほど日付が新しい
     * 一番上に書かれているものを用いる
* `recipe_id`
   * 各レシピに割り当てられるID
     * 例:`FriedRice_with_StarchySauce`
   * `http://{chiffon_server["host"]}:{chiffon_server["port"]}/woz/recipe/{session_id}`から取得可能
     * レシピはXMLで記述されている
     * `recipe_id`はrecipe要素のidとして指定されている



## TableObjectManager起動

TableObjectManagerはスクリプト内部で呼び出しされる。実行ファイルのパスは設定ファイルで指定する。後述の画像リサイズ,特徴量抽出プログラムも同様。

引数として画像を保存するディレクトリを指定する必要があるが、これは設定ファイル内のディレクトリ名を絶対パスに変換したものを指定する。その他の引数は設定ファイルで指定する。

作業エリアの内外をTableObjectManager認識させるために、マスク画像を利用することができる。

設定ファイルの `[table_object_manager] workspace_end_filename` パラメータで指定できる。

### workspace_end_filenameの仕様

以下の要件で作成した画像ファイルを指定する。

* 使用するカメラの 1/4 の画像を使用する。
  * 例) カメラが 480x640 の場合、120x160
* 作業エリア内外は2色で構成する。
  * 作業エリア内: 黒(\#000000)
  * 作業エリア外: 白(#ffffff)

### サンプルマスク画像
 example\\workspace_end_filename.png

 解像度が 1040x776 のときのサンプルマスク画像

## 画像のリサイズ

TableObjectManagerにより保存される画像は2種類ある。内1つは無編集の画像で、もう1つは対象物以外にマスクをかけたものである。この2つの画像を用いて256*256にリサイズした物体の画像を生成するプログラムをスクリプトから呼び出す。

引数として保存された2種類の画像のパスと出力する画像のパスを指定する必要がある。検出される画像はマスクをかけられた方の画像であり、このファイル名からもう1つの無編集の画像のパスを特定する。その他の引数は設定ファイルで指定する。



## 特徴量抽出

プログラムの引数として`{input_file}`,`{output_file}`を渡す必要がある。`{input_file}`には新しく保存された画像のパス、`{output_file}`には特徴量を保存するファイルのパス(設定ファイルに記述)を指定する。



## server4recog

### 送信するURLおよびクエリ

```
http://localhost:8080/ml/my_db/my_feature/svc/predict?json_data={${SAMPLE}, ${CLASSIFIER-PARAMS}}
```

`{SAMPLE}`は以下のパラメータを持つ。

* feature
   * サンプルの特徴量
   * 前の特徴量抽出プログラムにより出力されたファイルの中身が入る
* id
   * 入力するサンプルのID
   * 画像ファイルのbasenameを使う
* group
   * グループタグの名前
   * 起動時の引数で指定した`group_id`の他に`user_id`,`recipe_id`,`session_id`および設定ファイルで指定した`default_group`を配列の形で代入する

`{CLASSIFIER-PARAMS}`は以下のパラメータを持つ。

* name
   * 分類器の名前
   * `recipe_id`(レシピ名)を入れる

### objectidへの変換

server4recogから返ってくる認識結果は以下の様なjsonである。

```
{"tomato":0.4,"banana":0.3,...}
```

この認識結果のクラス名はCHIFFONへ渡す際に変換テーブル(`s4r_convtable.csv`)に基づいてレシピのobjectidに変換される。テーブル用のcsvファイルは以下のように記述する。

```
tomato,トマト
banana,バナナ
...
```



## CHIFFON

### 送信するURLおよびクエリ

```
http://chiffon.mm.media.kyoto-u.ac.jp/receiver?sessionid={sessionid}&string={string}
```

* sessionid
   * 起動時引数で指定した`session_id`と同一。
* string
   * 書式:`{"navigator":{navigator},"action":{"target":{target},"name":{name},"timestamp":{timestamp}}}`
   * `navigator`:
     * 設定ファイルで指定したものを用いる
   * `target`:操作対象
     * server4recogから返ってきたjsonのハッシュを代入する
   * `name`:操作の内容
     * `touch`(物を掴む動作)あるいは`release`(物を手放す動作)
     * 画像が保存されたディレクトリの名前が入る
   * `timestamp`:クエリ送信日時
     * 設定ファイルで指定したものを用いる
       * 例:`{"navigator":"object_access","action":{"target":"knife_utensil","name":"release","timestamp":"2015.12.08_15.06.27.710000"}}`

## 出力ファイルについて
出力ディレクトリ名、拡張子は設定ファイルに準じます。
出力ファイル名は、table_object_manager が出力したファイル名に準じます。

### ディレクトリ構造
* data/
  * [SESSION_ID]/
    * chiffon_server/
      * release/
      * touch/
    * image_feature_extractor/
      * release/
      * touch/
    * object_region_box_extractor/
      * PUT/
      * TAKEN/
    * serv4recog/
      * release/
      * touch/
    * table_object_manager/
      * PUT/
      * raw/
      * TAKEN/

### table_object_manager
table_object_manager が生成する、背景画像と背景差分画像を出力するディレクトリ。

* table_object_manager/
  * PUT/
    * putobject_0000046_000.png - 物を置いた際の差分画像
  * raw/
    * bg_0000003.png - 背景差分の基準となる背景画像
  * TAKEN/
    * takenobject_0000175_001.png - 物を取った際の差分画像
  * table_object_manager.log - table_object_manager の出力するログ

### object_region_box_extractor
特徴量抽出のために、差分が生じた部分を切り出した画像を出力するディレクトリ。

* object_region_box_extractor/
  * PUT/
    * putobject_0000046_000.png
  * TAKEN/
    * takenobject_0000175_001.png

### image_feature_extractor
切り出し済みの画像を用いて、特徴量を CSV 形式で出力する。

* image_feature_extractor/
  * release/
    * takenobject_0000175_001.csv
  * touch/
    * putobject_0000046_000.csv

### serv4recog
認識用プログラムに特徴量を渡す際の URL + クエリとその結果を保存するディレクトリ。
url + クエリは .log ファイル、結果は .json ファイルに記載する。

* serv4recog/
  * release/
    * takenobject_0000175_001.json
    * takenobject_0000175_001.log
  * touch/
    * putobject_0000046_000.json
    * putobject_0000046_000.log

### chiffon_server
認識用プログラムから得た結果を Chiffon Server に渡す際の URL + クエリとその結果を保存するディレクトリ。
url + クエリは .log ファイル、結果は .json ファイルに記載する。

* chiffon_server/
  * release/
    * takenobject_0000175_001.json
    * takenobject_0000175_001.log
  * touch/
    * putobject_0000046_000.json
    * putobject_0000046_000.log
