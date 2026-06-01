import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from speak_practice.models import ChatSession, UserSceneExposure
from speak_practice.views import _build_realtime_session_payload


User = get_user_model()


class RealtimePayloadTests(TestCase):
    def test_realtime_payload_waits_quietly_without_idle_nudge(self):
        user = User.objects.create_user(username='learner', password='pass1234')
        session = ChatSession.objects.create(user=user, scene='At a fruit market in Chengdu', scene_signature='fruit-market')

        payload = _build_realtime_session_payload(session, profile=None)
        instructions = payload['session']['instructions']
        turn_detection = payload['session']['audio']['input']['turn_detection']

        self.assertIn('Do not chase or pressure the learner if they stay silent', instructions)
        self.assertIsNone(turn_detection)


class TopicGenerationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='topic-user', password='pass1234')
        self.client.force_login(self.user)

    @patch('speak_practice.views._record_scene_exposures')
    @patch('speak_practice.views._get_template_topics_for_user', return_value=[])
    @patch('speak_practice.views.generate_dynamic_topic_cards')
    @patch('speak_practice.views._validate_request_origin', return_value=True)
    def test_load_topics_passes_recent_examples_to_generator(
        self,
        _mock_validate_origin,
        mock_generate_topics,
        _mock_template_topics,
        _mock_record_exposures,
    ):
        UserSceneExposure.objects.create(
            user=self.user,
            scene_title='Street Market Bargain',
            scene_text='You are bargaining for vegetables at a busy market.',
            scene_signature='street-market-bargain',
            scene_source='ai_generated',
            exposure_type='shown',
        )

        mock_generate_topics.return_value = [
            {
                'title': f'Topic {index}',
                'description': f'Description {index}',
                'level': 'Beginner',
                'icon': 'fas fa-comments',
                'scene_text': f'Scene text {index}',
            }
            for index in range(10)
        ]

        response = self.client.get(reverse('speak_practice:load_topics_api'))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(mock_generate_topics.called)
        recent_examples = mock_generate_topics.call_args.kwargs['recent_examples']
        self.assertIn('Street Market Bargain', recent_examples)


class CustomScenePromptTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='scene-user', password='pass1234')
        self.client.force_login(self.user)

    @patch('speak_practice.views._validate_request_origin', return_value=True)
    @patch('speak_practice.views.requests.post')
    def test_generate_scene_prompt_includes_recent_examples(self, mock_post, _mock_validate_origin):
        UserSceneExposure.objects.create(
            user=self.user,
            scene_title='Train Ticket Counter',
            scene_text='You are buying a high-speed rail ticket at the station.',
            scene_signature='train-ticket-counter',
            scene_source='ai_generated',
            exposure_type='selected',
        )

        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status.return_value = None
        mock_post.return_value.json.return_value = {
            'choices': [{
                'message': {
                    'content': json.dumps({
                        'scenarios': [{
                            'title': 'Night Market Snacks',
                            'description': 'Ordering food at a crowded night market.',
                            'level': 'Beginner',
                            'context': 'A casual street food conversation.',
                        }]
                    })
                }
            }]
        }

        response = self.client.post(
            reverse('speak_practice:generate_scene_api'),
            data=json.dumps({'user_input': 'travel conversation'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        payload = mock_post.call_args.kwargs['json']
        system_prompt = payload['messages'][0]['content']
        self.assertIn('Avoid ideas that are too similar to these recent scenes', system_prompt)
        self.assertIn('Train Ticket Counter', system_prompt)
