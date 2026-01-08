css = '''
<style>
.chat-container {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.chat-message {
    display: flex;
    align-items: flex-start;
    padding: 1.5rem;
    border-radius: 0.5rem;
    max-width: 80%;
    margin-bottom: 1.5rem;
}

.chat-message.user {
    background-color: #2b313e;
    margin-left: auto;              /* Align to the right */
    flex-direction: row-reverse;    /* Avatar on the right */
}

.chat-message.bot {
    background-color: #475063;
    margin-right: auto;             /* Align to the left */
    flex-direction: row;            /* Avatar on the left */
}

.chat-message .avatar {
    width: 20%;
    display: flex;
    justify-content: center;
    align-items: center;
}

.chat-message .avatar img {
    max-width: 48px;
    max-height: 48px;
    border-radius: 50%;
    object-fit: cover;
}

.chat-message .message {
    width: 80%;
    padding: 0 1.5rem;
    color: #fff;
    word-wrap: break-word;
}

.block-container {
    padding-top: 2rem !important;  /* Reduce from default ~6.25rem */
}

/* Styling for the Streamlit container that holds our figures */
.stImage {
    border: 1px solid #475063;
    border-radius: 5px;
    padding: 10px;
    background-color: #1e222b; /* Slightly darker than the bubble */
    margin-top: -1rem; /* Pull it closer to the chat bubble */
}

/* Make the figure subheader look integrated */
.assistant-fig-header {
    color: #ffd700; /* Gold color for visibility */
    font-size: 0.9rem;
    font-weight: bold;
    margin-top: 5px;
}

/* Optional: reduce vertical spacing between title and first element */
h1 {
    margin-top: 0rem;
    margin-bottom: 1rem;
}

/* Move sidebar content higher */
section[data-testid="stSidebar"] > div {
    padding-top: 1rem !important;  /* Reduce from default ~6.25rem */
}
</style>
'''

user_template = '''
<div class="chat-message user">
    <div class="avatar">
        <img src="https://i.ibb.co/5xMqBTCy/man.png" style="max-height: 78px; max-width: 78px; border-radius: 50%; object-fit: cover;">
    </div>    
    <div class="message">{{MSG}}</div>
</div>
'''

bot_template = '''
<div class="chat-message bot">
    <div class="avatar">
        <img src="https://i.ibb.co/jPpynhYk/virtual-assistant.png" style="max-height: 78px; max-width: 78px; border-radius: 50%; object-fit: cover;">
    </div>
    <div class="message">{{MSG}}</div>
</div>
'''

# bot_template = '''
# <div class="chat-message bot">
#     <div class="avatar">
#         <img src="https://i.ibb.co/cN0nmSj/Screenshot-2023-05-28-at-02-37-21.png" style="max-height: 78px; max-width: 78px; border-radius: 50%; object-fit: cover;">
#     </div>
#     <div class="message">{{MSG}}</div>
# </div>
# '''

