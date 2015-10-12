import os
files = os.listdir('/home/ubuntu/grouping_test/')
groups = sorted(set([item.split('_')[0] for item in files]))
html = """
<style>
li {
border:1px solid #000;
}
</style>"""
html += '<ul>'

for group in groups:
    html += '<li>'+group+'\n'
    for detection in sorted([item for item in files if item.startswith(group)]):
        html += '<img src="file:///Y://grouping_test/'+detection+'" />'
    html += '</li>'
html += '</ul>'
with open('/home/ubuntu/groups.html', 'w') as f:
    f.write(html)
