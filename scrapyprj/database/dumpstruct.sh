#!/bin/sh
mysqldump -d -p --triggers --routines --default-character-set=utf8mb4 $1 | sed -e 's/DEFINER[ ]*=[ ]*[^*]*\*/\*/' | sed 's/ AUTO_INCREMENT=[0-9]*\b//'