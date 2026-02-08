from flask import Flask, jsonify, request
from utils import request_get

app = Flask(__name__)
manifest_url_api = "https://loadingbaycn.webapp.163.com/app/v1/file_distribution_v2/manifest_url"

@app.route('/app/v1/file_distribution_v2/manifest_url', methods=['GET'])
def get_manifest():
    app_content_id = request.args.get('app_content_id')
    target_version = request.args.get('target_version')
    downloadable_id = int(target_version.split("_")[1]) if target_version and "_" in target_version else None

    # format 1: by target_version
    params = {
        "app_content_id": app_content_id,
        "target_version": target_version
    }
    manifest_data = request_get(manifest_url_api, params=params)
    if manifest_data is not None and manifest_data.get("code") == 200:
        manifest_data_data = manifest_data.get("data", {})
        target_downloadable_id = manifest_data_data.get("downloadable_id")
        if target_downloadable_id is not None and target_downloadable_id == downloadable_id:
            print(f"[*] Found manifest for version {target_version}")
            return jsonify(manifest_data), 200
    else:
        print(f"[!] No manifest found for app_content_id {app_content_id}")
        return jsonify({
            "code": 500,
            "msg": "Failed to get manifest URL"
        }), 200
    manifest_template = manifest_data
    
    # format 2: by downloadable_id
    params = {
        "app_content_id": app_content_id,
        "target_downloadable_id": downloadable_id
    }
    manifest_data = request_get(manifest_url_api, params=params)
    if manifest_data is not None and manifest_data.get("code") == 200:
        print(f"[*] Found manifest for downloadable_id {downloadable_id}")
        return jsonify(manifest_data), 200
    
    # format 3: fallback to construct manifest URL
    if not downloadable_id:
        print("[!] Missing downloadable_id for fallback manifest URL construction")
        return jsonify({
            "code": 500,
            "msg": "Failed to get manifest URL"
        }), 200
    print(f"[*] Fallback to construct manifest URL for downloadable_id {downloadable_id}")
    manifest_template["data"]["manifest_url"] = f"https://x19-h.gdl.netease.com/a50_package__v2_i_81_{downloadable_id}/v2_569_{downloadable_id}.manifest"
    manifest_template["data"]["downloadable_id"] = downloadable_id
    return jsonify(manifest_template), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7000, debug=False)
