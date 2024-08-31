from typing import Any
from ninja import NinjaAPI
from ninja.openapi.docs import DocsBase
from django.http import HttpRequest, HttpResponse

class Rapidoc(DocsBase):
    def render_page(self, request, api):
        js_url = f"https://unpkg.com/rapidoc/dist/rapidoc-min.js"
        openapi_schema = "/api/openapi.json"

        html = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <meta charset="utf-8"/>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <script src="{js_url}" crossorigin></script>
            </head>
            <body>
                <rapi-doc spec-url="{openapi_schema}" />
            </body>
        </html>
        """

        return HttpResponse(html)
    

class Elements(DocsBase):
    def render_page(self, request, api):
        js_dist='https://unpkg.com/@stoplight/elements/web-components.min.js'
        css_dist='https://unpkg.com/@stoplight/elements/styles.min.css'
        openapi_schema = "/api/openapi.json"

        html=F"""
        <!DOCTYPE html>
        <html>
            <head>
                <title>imperai API</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
                <script src="{js_dist}"></script>
                <link rel="stylesheet" href="{css_dist}">
            </head>
            <body>
                <elements-api apiDescriptionUrl="{openapi_schema}" router="hash" layout="responsive" />
            </body>
        </html>
        """
        return HttpResponse(html)
    


class Scalar(DocsBase):
    def render_page(self, request, api) -> HttpResponse:
        yaml_dataurl = "https://cdn.jsdelivr.net/npm/@scalar/galaxy/dist/latest.yaml"
        openapi_schema = "/api/openapi.json"
        css_cust='static/css/scalar_mars.css'
        cust_script="var configuration = {theme: 'mars', withDefaultFonts: 'false'}"
        html = f"""
        <!doctype html>
        <html>
            <head>
                <title>imperai API reference</title>
                <meta charset="utf-8" />
                <meta
                name="viewport"
                content="width=device-width, initial-scale=1" />
                <script>{cust_script}</script>
            </head>
            <body>
                <!-- Need a Custom Header? Check out this example https://codepen.io/scalarorg/pen/VwOXqam -->
                <script
                id="api-reference"
                data-url="{openapi_schema}"></script>
                
                <script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>
            </body>
        </html>
        """
        return HttpResponse(html)