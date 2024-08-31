from django.contrib import admin
from .models import UploadedFile, FileTextExtraction, Conversation, Message

class PTEInline(admin.TabularInline):
    model = FileTextExtraction
    extra = 0

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0

class UploadedFileAdmin(admin.ModelAdmin):
    readonly_fields = ('id_external', 'uploaded_at')
    inlines = [
        PTEInline,
    ]

admin.site.register(UploadedFile, UploadedFileAdmin)

class FileTextExtractionAdmin(admin.ModelAdmin):
    readonly_fields = ('id_external', 'processed_at')

admin.site.register(FileTextExtraction, FileTextExtractionAdmin)

class ConversationAdmin(admin.ModelAdmin):
    readonly_fields = ('id_external', 'created_at')
    inlines = [
        MessageInline,
    ]

admin.site.register(Conversation, ConversationAdmin)

class MessageAdmin(admin.ModelAdmin):
    readonly_fields = ('id_external', 'created_at')

admin.site.register(Message, MessageAdmin)
