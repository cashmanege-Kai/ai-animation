# Kaggle 人物替換測試包

新增流程，保留原本的木偶測試與檔案。來源舞台為籃球，角色穿網球服，不改成網球比賽。

1. Kaggle建立私人Notebook，匯入kaggle-wan-animate-recast.ipynb；啟用Internet與GPU。
2. 將本包附件加入私人Input。原片source-zYt0aOGDwP0.mp4另作私人Input，**不在公開GitHub散布第三方原片**。
3. 執行GPU檢查，再將INSTALL_ENVIRONMENT改True，建立獨立ComfyUI。Windows原安裝不更動。
4. 自行附加官方模型Dataset並檢查缺檔。此包不含或自動下載大型模型，也不含API金鑰。
5. 準備77幀/16fps/432×768靜音短段及角色圖。正式人物替換需人物遮罩與API JSON；Notebook中的官方UI工作流程不可直接提交/prompt。
6. 必須在可用的ComfyUI編輯介面選取人物、核對遮罩，再匯出tennis-recast-api.json作Input。**本包尚不提供Kaggle遠端UI通道，不是下載後就能一鍵完整替換的成品。**
7. START_SERVER及RUN_GENERATION預設False，確認環境與遮罩後才開啟。依實際GPU/系統RAM決定是否能跑；無法保證16GB可以順暢跑14B。
8. 首次短段驗收後再擴充至16秒，避免多鏡/遮擋造成錯誤。輸出位於/kaggle/working/exports，請儲存Kaggle版本。

檔案：Notebook、輸入準備程式、API提交器、官方UI模板、網球服角色參考圖。語法與本機輸入準備會驗證；尚未在Kaggle GPU上實跑。

官方文件：https://docs.comfy.org/tutorials/video/wan/wan2-2-animate
模板來源：https://raw.githubusercontent.com/Comfy-Org/workflow_templates/main/templates/video_wan2_2_14B_animate.json

公開庫請勿上傳work/API KEY.txt、.env、任何Token、模型權重、第三方原片及其音樂。

