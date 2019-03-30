package syncer

import (
	"fmt"

	"github.com/andygrunwald/go-jira"
	"github.com/sirupsen/logrus"

	"github.com/legionus/jiramail/internal/jiraconv"
	"github.com/legionus/jiramail/internal/jiraplus"
)

func (s *JiraSyncer) epic(board *jira.Board, epic *jira.Epic, refs []string) error {
	epicName := fmt.Sprintf("%s (%d)", ReplaceStringTrash(epic.Name), epic.ID)

	logmsg := fmt.Sprintf("remote %q, board %q, epic %q", s.remote, board.Name, epicName)
	logrus.Infof("%s begin to process", logmsg)

	mdir, err := Maildir(s.getPath(s.config.Mail.Path.Epic))
	if err != nil {
		return err
	}

	// write epic to the epic maildir
	msg, err := s.converter.Epic(epic, append(refs, jiraconv.BoardMessageID(board)))
	if err != nil {
		return err
	}

	err = s.writeMessage(mdir, msg)
	if err != nil {
		return err
	}

	// write board to the epic maildir
	msg, err = s.converter.Board(board, "reply+epic@jira", refs)
	if err != nil {
		return err
	}

	err = s.writeMessage(mdir, msg)
	if err != nil {
		return err
	}

	refs = append(refs, jiraconv.BoardMessageID(board), jiraconv.EpicMessageID(epic))

	opts := &jiraplus.BoardIssuesSearchOptions{}
	opts.MaxResults = 100
	opts.Fields = []string{"*all"}

	count, err := jiraplus.List(
		func(i int) ([]interface{}, error) {
			opts.StartAt = i

			ret, _, err := s.client.PlusBoard.GetIssuesForEpic(board.ID, epic.ID, opts)
			if err != nil {
				return nil, fmt.Errorf("unable to get issues for epic '%s': %s", epic.Key, err)
			}

			if ret.Total <= i {
				return nil, nil
			}

			a := make([]interface{}, len(ret.Issues))

			for k := range ret.Issues {
				a[k] = ret.Issues[k]
			}

			return a, nil
		},
		func(o interface{}) error {
			issue := o.(*jira.Issue)

			if issue.Fields == nil || issue.Fields.Type.Subtask {
				return nil
			}

			if err := s.issue(mdir, issue, refs); err != nil {
				return err
			}

			if err := s.projectissue(issue); err != nil {
				return err
			}

			return nil
		},
	)
	if err != nil {
		return err
	}

	logrus.Infof("%s, %d issues handled", logmsg, count)

	// Garbage collection
	err = s.CleanDir(mdir)
	if err != nil {
		return err
	}

	return nil
}

func (s *JiraSyncer) epics(board *jira.Board, refs []string) error {
	if s.config.Mail.Path.Epic == "" {
		return nil
	}

	opts := &jira.SearchOptions{}
	opts.MaxResults = 100

	_, err := jiraplus.List(
		func(i int) ([]interface{}, error) {
			opts.StartAt = i

			ret, _, err := s.client.PlusBoard.GetEpics(board.ID, opts)
			if err != nil {
				return nil, err
			}

			a := make([]interface{}, len(ret.Values))

			for k := range ret.Values {
				a[k] = ret.Values[k]
			}

			return a, nil
		},
		func(o interface{}) error {
			epic := o.(*jira.Epic)

			s.vars["EpicName"] = ReplaceStringTrash(epic.Name)
			s.vars["EpicID"] = fmt.Sprintf("%d", epic.ID)

			err := s.epic(board, epic, refs)
			if err != nil {
				return err
			}

			return nil
		},
	)

	delete(s.vars, "EpicName")
	delete(s.vars, "EpicID")

	return err
}
