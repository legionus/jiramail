package message

import (
	"bufio"
	"bytes"
	"strings"
)

func BodyFromStrings(strs ...string) (body []string, err error) {
	for _, s := range strs {
		scanner := bufio.NewScanner(strings.NewReader(s))

		for scanner.Scan() {
			body = append(body, scanner.Text())
		}
		if err = scanner.Err(); err != nil {
			return nil, err
		}
	}
	return body, nil
}

func BodyFromBytes(arr ...[]byte) (body []string, err error) {
	for _, data := range arr {
		scanner := bufio.NewScanner(bytes.NewReader(data))

		for scanner.Scan() {
			body = append(body, scanner.Text())
		}
		if err = scanner.Err(); err != nil {
			return nil, err
		}
	}
	return body, nil
}
