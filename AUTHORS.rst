#######
AUTHORS
#######
(in chronological order)

- Ralf Schmitt            <ralf@systemexit.de>,
- Kostis Anagnostopoulos  <ankostis@gmail.com>
- Matthew Planchard       <mplanchard@gmail.com>
- run  ``git log --format='%aN' | sort -u`` to see all contributors, or::

      git log --format='%aN <%aE>' |
        awk '{arr[$0]++} END{for (i in arr){print arr[i], i;}}' |
        sort -rn | cut -d\  -f2-

  to sort them by the numbers of commits.
