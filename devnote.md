## Project Overview
The system is for learnchineseperth, a chinese school in Perth. in the system, we will include applications for students mainly, like typing, reading comprehension, listening, and speaking. so the UI should be professional, clean, and easy to use.

## Tasks
- [x] change dns afterclass.learnchineseperth.com.au to 170.64.162.255
- [x] a .sh file to restart django project with gunicorn. be sure collect statics, make migrations, migrate, restart gunicorn. understand the codebase then come up the script.
- [] pinyinit, add print button to print the pinyin file;

## Typing Chinese
- [] make a django application for typing. the feature has the following workflow:
1. users start with a textarea input and a generate text button
2. users can either input some text, or click the generate text button to trigger a modal to ask users to speicify topic and expected length of the text, then AI will use the information to generate a random text
3. there is a "start typing" button below the textarea if the textarea is not empty. when clicked, it will direct users to a new page, with left-right split layout, left side is the text that input in the previous page to type, right side is the typing interface (textarea?).
4. there is a checkbox for the users to select if they want to show the pinyin of the text in the left side or not. 


## UI 
theme colour:
#FE4D01
#FFD966
#ffffff

text colour:
#151515
#333333
